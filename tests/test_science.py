from dataclasses import replace
from datetime import date
import json
import math
import numpy as np
import pandas as pd
import pytest

from agroshift.climate import Window, aggregate, dry_spell, season_samples, seasonal_summary
from agroshift.decision import Farm, assess, normalized_weights
from agroshift.power import DataError, load_snapshot
from agroshift.reporting import report_html, report_json

@pytest.fixture(scope="module")
def data():
    return load_snapshot("data/demo_power.json")

@pytest.fixture
def farm():
    return Farm(drainage="well_drained",ph=6.5,pilot_confirmed=True)

WEIGHTS={"temperature":25,"water":25,"soil":25,"diversification":25}

def test_real_snapshot(data):
    assert len(data.frame)==9131
    assert data.frame.index.min()==pd.Timestamp("2001-01-01")
    assert data.frame.index.max()==pd.Timestamp("2025-12-31")
    assert data.provenance["mode"]=="bundled NASA snapshot"

def test_complete_month_and_missing_rain(data):
    frame=data.frame.loc["2024-02"].copy()
    assert aggregate(frame).iloc[0].rainfall_mm==pytest.approx(frame.PRECTOTCORR.sum())
    frame.iloc[0,frame.columns.get_loc("PRECTOTCORR")]=np.nan
    result=aggregate(frame).iloc[0]
    assert math.isnan(result.rainfall_mm)
    assert result.rain_coverage==pytest.approx(28/29)

def test_partial_year_is_not_complete(data):
    assert math.isnan(aggregate(data.frame.loc["2024-01":"2024-06"],"YS").iloc[0].rainfall_mm)

def test_temperature_coverage(data):
    frame=data.frame.loc["2024-01"].copy()
    frame.loc[frame.index[:5],"T2M"]=np.nan
    assert math.isnan(aggregate(frame).iloc[0].temperature_c)

def test_dry_spell_missing_and_boundary():
    assert dry_spell(pd.Series([0,0,np.nan,0,0,0,1,0]))==(3,True)
    assert dry_spell(pd.Series([.9,1,0,0]))==(2,False)

def test_cross_year_season(data):
    samples=season_samples(data.frame,Window(11,1,2,28))
    assert len(samples)==24
    assert samples.year.max()==2024
    assert samples.iloc[0].days==120

def test_scenario_is_copy(data):
    original=data.frame.copy(deep=True)
    w=Window(4,15,7,31)
    a=season_samples(data.frame,w)
    b=season_samples(data.frame,w,.5,2)
    assert b.rainfall_mm.iloc[0]==pytest.approx(.5*a.rainfall_mm.iloc[0])
    assert b.temperature_c.iloc[0]==pytest.approx(a.temperature_c.iloc[0]+2)
    pd.testing.assert_frame_equal(original,data.frame)

@pytest.mark.parametrize("weights", [{k:0 for k in WEIGHTS},dict(WEIGHTS,water=-1),dict(WEIGHTS,water=float('nan'))])
def test_invalid_weights(weights):
    with pytest.raises(DataError): normalized_weights(weights)

def test_weights_normalize():
    assert sum(normalized_weights(WEIGHTS).values())==pytest.approx(1)

def test_existing_plan_always_included(data,farm):
    results=assess(data.frame,replace(farm,allowed=("maize","groundnut")),WEIGHTS)
    assert len(results)==5
    assert sum(r["baseline"] for r in results)==1

def test_waterlogging_blocks_regardless_of_weight(data,farm):
    results=assess(data.frame,replace(farm,drainage="waterlogged"),dict(temperature=0,water=0,soil=0,diversification=100))
    assert next(r for r in results if r["sequence"]==("rice","mung_bean"))["status"]=="Blocked"

def test_unknown_soil_widens_interval(data,farm):
    a={r['id']:r for r in assess(data.frame,farm,WEIGHTS)}
    b={r['id']:r for r in assess(data.frame,replace(farm,ph=None,drainage="unknown"),WEIGHTS)}
    key="cowpea__cowpea"
    assert b[key]["high"]-b[key]["low"] > a[key]["high"]-a[key]["low"]

def test_priority_changes_components_order(data,farm):
    a=assess(data.frame,farm,dict(temperature=100,water=0,soil=0,diversification=0))
    b=assess(data.frame,farm,dict(temperature=0,water=0,soil=0,diversification=100))
    assert [r['id'] for r in a] != [r['id'] for r in b]

def test_water_scenario_monotone(data,farm):
    dry=replace(farm,rain_fraction=.2,irrigation="supplemental",irrigation_mm=0)
    wet=replace(dry,irrigation_mm=400)
    a={r['id']:r for r in assess(data.frame,dry,WEIGHTS)}
    b={r['id']:r for r in assess(data.frame,wet,WEIGHTS)}
    assert b["maize__maize"]["components"]["water"]["low"]>a["maize__maize"]["components"]["water"]["low"]
    assert b["rice__rice"]["components"]["water"]["low"]==0
    assert b["mung_bean__mung_bean"]["components"]["water"]["high"]==1

def test_insufficient_history(data,farm):
    with pytest.raises(DataError,match="ten complete"):
        assess(data.frame.loc["2024":],farm,WEIGHTS)

def test_overlapping_seasons_rejected(farm):
    with pytest.raises(DataError,match="overlap"):
        replace(farm,windows=(Window(11,1,2,28),Window(1,1,4,1))).validate()

@pytest.mark.parametrize("field,value",[("ph",float('nan')),("area_ha",0),("irrigation_mm",-1),("rain_fraction",1.2)])
def test_invalid_farm(farm,field,value):
    with pytest.raises(DataError):replace(farm,**{field:value}).validate()

def test_reports_escape_and_preserve_unknowns(data,farm):
    farm=replace(farm,nutrients="<script>alert('x')</script>",ph=None)
    results=assess(data.frame,farm,WEIGHTS)
    text=report_html(data,farm,WEIGHTS,results)
    assert "<script>" not in text and "&lt;script&gt;" in text
    record=json.loads(report_json(data,farm,WEIGHTS,results))
    assert record["farm"]["ph"] is None
    assert record["provenance"]["sha256"]==data.provenance["sha256"]
    assert record["comparison"][0]["components"]

def test_reference_fields_have_sources():
    from agroshift.decision import CROPS,KNOWLEDGE
    for crop in CROPS.values():
        for field,source in [("water_mm","water_source"),("temperature_c","temperature_source"),("duration_days","duration_source")]:
            if crop[field] is not None:
                assert crop[source] in KNOWLEDGE["sources"]

def test_three_documented_demo_scenarios(data):
    # Scenario 1: Well-drained lowland transition with measured pH 6.5
    s1_farm = Farm(drainage="well_drained", ph=6.5, pilot_confirmed=True)
    s1 = {r["id"]: r for r in assess(data.frame, s1_farm, WEIGHTS)}
    assert s1["cowpea__mung_bean"]["status"] == "Conditional exploration"
    assert s1["cowpea__mung_bean"]["low"] > s1["rice__rice"]["low"]

    # Scenario 2: Explicit water-screening assumption (rain_fraction=0.35, supplemental irrigation)
    s2_low_irrig = replace(s1_farm, rain_fraction=0.35, irrigation="supplemental", irrigation_mm=50.0)
    s2_high_irrig = replace(s1_farm, rain_fraction=0.35, irrigation="supplemental", irrigation_mm=400.0)
    r_low = {r["id"]: r for r in assess(data.frame, s2_low_irrig, WEIGHTS)}
    r_high = {r["id"]: r for r in assess(data.frame, s2_high_irrig, WEIGHTS)}
    assert r_high["maize__groundnut"]["components"]["water"]["low"] > r_low["maize__groundnut"]["components"]["water"]["low"]
    assert r_high["maize__groundnut"]["components"]["water"]["low"] > 0.5
    assert r_high["rice__rice"]["components"]["water"]["low"] == 0.0
    assert r_high["rice__rice"]["components"]["water"]["high"] == 1.0

    # Scenario 3: Unknown pH/nutrients and persistent waterlogging
    s3_farm = Farm(drainage="waterlogged", ph=None, nutrients="Unknown", pilot_confirmed=True)
    s3 = {r["id"]: r for r in assess(data.frame, s3_farm, WEIGHTS)}
    assert s3["rice__rice"]["status"] == "Conditional exploration"
    for key, res in s3.items():
        if key != "rice__rice":
            assert res["status"] == "Blocked"
            assert res["constraints"]

def test_global_climate_evidence_nairobi_and_ames(data, farm):
    from agroshift.power import parse_payload, request_parameters
    for fname, lat, lon, cc in [
        ("preparation/evidence/nairobi_20250101_20250107.json", -1.2921, 36.8219, "KE"),
        ("preparation/evidence/ames_20250101_20250107.json", 42.0308, -93.6319, "US"),
    ]:
        with open(fname, encoding="utf-8") as fh:
            payload = json.load(fh)
        query = request_parameters(lat, lon, date(2025, 1, 1), date(2025, 1, 7))
        frame, issues = parse_payload(payload, query)
        assert len(frame) == 7 and not issues

def test_anomaly_classification_and_demo_presets(data, farm):
    from agroshift.presets import DEMO_SCENARIOS
    from agroshift.climate import classify_anomalies
    samples = classify_anomalies(season_samples(data.frame, farm.windows[0]))
    assert "rainfall_z" in samples.columns and "regime" in samples.columns
    assert set(samples["regime"]).issubset({
        "Dry anomaly (z < -1.0)",
        "Wet anomaly (z > +1.0)",
        "Typical range (-1.0 ≤ z ≤ +1.0)",
        "Incomplete coverage",
    })
    for key, preset in DEMO_SCENARIOS.items():
        preset["farm"].validate()
        res = assess(data.frame, preset["farm"], WEIGHTS)
        assert len(res) > 0
