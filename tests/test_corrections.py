"""Regressions from the scientific audit. Network failures are injected locally."""
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
import requests
from streamlit.testing.v1 import AppTest

from agroshift.assistant import assess_global_rotations, eligible_crops_and_rotations, query_optional_gemini
from agroshift.climate import Window, aggregate, compute_daily_agromet_indices, season_samples
from agroshift.decision import CRITERIA, CROPS, Farm, assess, priority_sensitivity
from agroshift.global_atlas import simulate_climate
from agroshift.ml_engine import forecast_seasonal_climate_timeseries
from agroshift.power import DataError, PowerClient, load_snapshot, unpack
from agroshift.reporting import report_json

WEIGHTS = dict.fromkeys(CRITERIA,25)

@pytest.fixture(scope="module")
def observed():
    return load_snapshot("data/demo_power.json")


def test_simulation_cannot_enter_any_farm_result():
    sim = simulate_climate(8.3114,80.4037)
    farm = Farm(pilot_confirmed=True)
    assert sim.provenance["data_kind"] == "SIMULATED"
    for action in (lambda:assess(sim.frame,farm,WEIGHTS),
                   lambda:eligible_crops_and_rotations(sim,farm,WEIGHTS),
                   lambda:report_json(sim,farm,WEIGHTS,[])):
        with pytest.raises(DataError,match="verified NASA"):
            action()


def test_reject_mismatched_location_or_period_even_with_valid_payload_hash(observed):
    envelope=json.loads(Path("data/demo_power.json").read_text())
    envelope["request"]["latitude"] += 1
    with pytest.raises(DataError,match="metadata"):
        unpack(envelope,"local cache")
    with pytest.raises(DataError,match="coordinates"):
        assess(observed.frame,Farm(latitude=8.32,pilot_confirmed=True),WEIGHTS)


def test_outage_uses_verified_distributed_archive_only(tmp_path):
    session=Mock()
    session.get.side_effect=requests.Timeout
    client=PowerClient(tmp_path,session=session,sleep=lambda seconds:None)
    row=pd.read_csv("data/global_nasa_stations_summary.csv").query("hub_key=='nairobi_kenya'").iloc[0]
    data=client.fetch(row.latitude,row.longitude,date(2001,1,1),date(2025,12,31))
    assert data.provenance["sha256"]==row.sha256
    assert data.provenance["data_kind"]=="VERIFIED_CACHE" and not data.provenance["simulated"]
    assert aggregate(data.frame,"YS").rainfall_mm.count()>0
    with pytest.raises(DataError,match="limited"):
        assess(data.frame,Farm(country="KE",latitude=row.latitude,longitude=row.longitude),WEIGHTS)
    with pytest.raises(DataError,match="connection failed"):
        client.fetch(row.latitude+.01,row.longitude,date(2001,1,1),date(2025,12,31))


def test_missing_environmental_values_are_never_generated(observed):
    part=observed.frame.iloc[:31].drop(columns=["T2M_MIN","RH2M","ALLSKY_SFC_SW_DWN"])
    derived=compute_daily_agromet_indices(part)
    assert all(np.isnan(derived[k]) for k in ["et0_mm","rh2m_pct","vpd_kpa","solar_mj_m2_day","days_tmin_below_0c"])
    partial=observed.frame.iloc[:30]
    assert np.isnan(aggregate(partial).iloc[0].et0_mm)


def test_crop_specific_evidence_and_duration_guards(observed):
    assert CROPS["maize"]["temperature_c"] is None
    assert CROPS["cowpea"]["temperature_c"]==[20,30]
    farm=Farm(pilot_confirmed=True,windows=(Window(4,1,5,10),Window(11,1,2,28)))
    results={r["id"]:r for r in assess(observed.frame,farm,WEIGHTS)}
    assert results["cowpea__rice"]["status"]=="Blocked"
    assert results["mung_bean__rice"]["status"]!="Blocked"
    specific=assess(observed.frame,replace(farm,mung_cultivar="MI 6"),WEIGHTS)
    assert next(r for r in specific if r["id"]=="mung_bean__rice")["status"]=="Blocked"
    assert (results["maize__maize"]["components"]["temperature"]["low"],
            results["maize__maize"]["components"]["temperature"]["high"])==(0,1)


def test_missing_water_stays_unknown_even_with_reliable_irrigation(observed):
    farm=Farm(pilot_confirmed=True,irrigation="reliable",rain_fraction=.5)
    results=assess(observed.frame,farm,WEIGHTS)
    assert farm.ph is None and farm.irrigation_mm is None
    assert all(r["components"]["water"]["low"]==0 and r["components"]["water"]["high"]==1 for r in results)
    assert results == assess_global_rotations(observed.frame, farm, WEIGHTS)
    assert set(CRITERIA)=={row["Criterion"] for row in priority_sensitivity(results,WEIGHTS)}
    assert not any(r["ordering_resolved"] for r in results)


def test_backtest_predictions_precede_outcomes(observed):
    samples=season_samples(observed.frame,Farm().windows[0])
    base=forecast_seasonal_climate_timeseries(samples)
    samples.loc[samples.index[-1],"rainfall_mm"]+=10000
    changed=forecast_seasonal_climate_timeseries(samples)
    assert base["series"][-1]["predicted_rain_mm"]==changed["series"][-1]["predicted_rain_mm"]
    assert changed["test_mae_rain_mm"]>base["test_mae_rain_mm"]
    assert "forecast_rainfall_mm" not in base


def test_optional_model_cannot_inject_an_agricultural_claim():
    brief=dict(period="20010101–20251231",provenance_mode="cache",total_candidates=25,
               blocked_candidates=0,farm_inputs={"irrigation":"unknown"})
    session=Mock()
    def output(ids):
        return {"candidates":[{"content":{"parts":[{"text":json.dumps(ids)}]}}]}
    session.post.return_value.json.return_value=output(["coverage"])
    assert "25 sequences" in query_optional_gemini("Summary",brief,"test",session)
    session.post.return_value.json.return_value=output(["Guaranteed yield of 20 tons"])
    with pytest.raises(DataError):
        query_optional_gemini("Summary",brief,"test",session)


def test_exported_report_matches_displayed_intervals(monkeypatch):
    import agroshift.reporting as reporting
    original=reporting.report_json
    exported=[]
    def capture(*args,**kwargs):
        raw=original(*args,**kwargs)
        exported.append(json.loads(raw))
        return raw
    monkeypatch.setattr(reporting,"report_json",capture)
    from test_app import demo,topic
    app=demo();topic(app,"Rotation comparison")
    table=next(item.value for item in app.dataframe if "Preference interval" in item.value)
    displayed=dict(zip(table["Rotation"],table["Preference interval"]))
    topic(app,"Downloads")
    assert not app.exception and len(app.get("download_button"))==5
    record=exported[-1]
    assert displayed=={r["name"]:f"{r['low']:.1f}–{r['high']:.1f}" for r in record["comparison"]}
    assert "fictional" in record["input_origin"]
    assert record["provenance"]["data_kind"]=="VERIFIED_CACHE"
    assert not any(k in json.dumps(record) for k in ["expected_output_t","ai_hybrid_score","success_probability"])

def test_wizard_outage_never_reuses_demo_or_simulates(monkeypatch):
    from agroshift import finder_ui
    from test_app import demo, click, select
    app=demo()
    original = finder_ui.load_history
    monkeypatch.setattr(finder_ui,"load_history",Mock(side_effect=DataError("injected outage")))
    click(app,"Start another farm")
    select(app,"Country or territory","KE")
    select(app,"Find your field","Saved locations")
    select(app,"Location","nairobi_kenya")
    click(app,"Use this location")
    assert not app.exception and app.session_state["dataset"] is None and not app.session_state["cards"]
    assert any("unavailable" in m.value.lower() for m in app.error)
    monkeypatch.setattr(finder_ui, "load_history", original)
    click(app, "Use this location")
    assert app.session_state["page"] == "conditions"
    assert app.session_state["dataset"].frame.attrs["latitude"] == -1.2921
    assert not app.session_state["cards"]
