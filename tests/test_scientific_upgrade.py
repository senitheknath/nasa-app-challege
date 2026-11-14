"""Comprehensive tests for the Master Scientific Engineering and Automation Upgrade."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from agroshift.aquacrop_prototype import run_aquacrop_water_driven_prototype
from agroshift.climate import Window, compute_daily_agromet_indices
from agroshift.decision import Farm
from agroshift.evidence_combination import CLASSIFICATION_LABELS, build_evidence_layers
from agroshift.extremes import summarize_historical_extremes
from agroshift.knowledge import (
    clear_cache,
    count_crops,
    crop_by_id,
    cultivar_traits,
    growth_stages,
    pest_context,
    refresh_policies,
    soil_observations,
)
from agroshift.pests import evaluate_crop_pest_context
from agroshift.power import (
    DataError,
    EXTENDED_PARAMETERS,
    PowerClient,
    archived_history,
    load_snapshot,
    parse_payload,
    power_grid_cell,
    request_parameters,
)
from agroshift.providers import (
    GAEZ_CROPS,
    chirps_context,
    gaez_point,
    gaez_polygon,
    match_crop_calendar,
    soil_profile_wcs,
    usda_sda_soil,
    wosis_profiles,
)
from agroshift.refresh_manager import evaluate_refresh_governance
from agroshift.rotation import evaluate_transition, plan_global_rotations
from agroshift.screening import find_options
from agroshift.soil import (
    classify_usda_texture,
    interpret_soil_profile,
    normalize_soilgrids_value,
    reconcile_soil_evidence,
)
from agroshift.validation import (
    evaluate_missing_data_stress,
    evaluate_temporal_holdout,
    run_ablation_study,
)
from agroshift.water_balance import (
    build_daily_kc_curve,
    compute_fao56_penman_monteith_daily,
    seasonal_water_balance_summary,
    simulate_season_crop_water_balance,
)

ROOT = Path(__file__).resolve().parents[1]


def test_extended_power_parameters_and_grid_cell_provenance(tmp_path):
    q = request_parameters(
        8.3114,
        80.4037,
        date(2023, 5, 1),
        date(2023, 5, 3),
        parameters=EXTENDED_PARAMETERS,
    )
    assert "WS2M" in q["parameters"] and "PS" in q["parameters"] and "GWETROOT" in q["parameters"]

    days = ["20230501", "20230502", "20230503"]
    payload = {
        "header": {
            "title": "NASA/POWER CERES/MERRA2 Native Resolution Daily Data",
            "api": {"version": "v2.5.0", "name": "POWER Daily API"},
            "sources": ["MERRA2", "CERES"],
            "fill_value": -999.0,
            "time_standard": "LST",
            "start": "20230501",
            "end": "20230503",
        },
        "geometry": {"type": "Point", "coordinates": [80.4037, 8.3114, 88.0]},
        "parameters": {
            "T2M": {"units": "C"},
            "T2M_MIN": {"units": "C"},
            "T2M_MAX": {"units": "C"},
            "T2MDEW": {"units": "C"},
            "PRECTOTCORR": {"units": "mm/day"},
            "RH2M": {"units": "%"},
            "ALLSKY_SFC_SW_DWN": {"units": "MJ/m^2/day"},
            "WS2M": {"units": "m/s"},
            "WS10M": {"units": "m/s"},
            "PS": {"units": "kPa"},
            "GWETTOP": {"units": "1"},
            "GWETROOT": {"units": "1"},
        },
        "properties": {
            "parameter": {
                "T2M": {d: 28.0 for d in days},
                "T2M_MIN": {d: 24.0 for d in days},
                "T2M_MAX": {d: 33.0 for d in days},
                "T2MDEW": {d: 22.0 for d in days},
                "PRECTOTCORR": {d: 4.5 for d in days},
                "RH2M": {d: 74.0 for d in days},
                "ALLSKY_SFC_SW_DWN": {d: 21.0 for d in days},
                "WS2M": {d: 2.2 for d in days},
                "WS10M": {d: 3.0 for d in days},
                "PS": {d: 100.4 for d in days},
                "GWETTOP": {d: 0.55 for d in days},
                "GWETROOT": {d: 0.62 for d in days},
            }
        },
    }
    frame, issues = parse_payload(payload, q)
    assert not issues
    assert list(frame.columns) == list(EXTENDED_PARAMETERS)

    # Out-of-bounds GWETTOP (>1) and negative WS2M are marked missing, not kept
    bad_payload = deepcopy(payload)
    bad_payload["properties"]["parameter"]["GWETTOP"]["20230502"] = 1.5
    bad_payload["properties"]["parameter"]["WS2M"]["20230502"] = -2.0
    frame_bad, issues_bad = parse_payload(bad_payload, q)
    assert pd.isna(frame_bad.loc["2023-05-02", "GWETTOP"])
    assert pd.isna(frame_bad.loc["2023-05-02", "WS2M"])
    assert len(issues_bad) == 2

    # Grid cell metadata & opt-in grid-cell cache reuse
    cell1 = power_grid_cell(8.3114, 80.4037)
    cell2 = power_grid_cell(8.3150, 80.4050)
    assert cell1["cell_id"] == cell2["cell_id"]

    class DummyResponse:
        status_code = 200
        url = "https://power.larc.nasa.gov/api/temporal/daily/point?test=1"
        headers = {}

        def json(self):
            return payload

    class DummySession:
        def __init__(self):
            self.calls = 0

        def get(self, *args, **kwargs):
            self.calls += 1
            return DummyResponse()

    sess = DummySession()
    client = PowerClient(cache_dir=tmp_path, session=sess)
    ds1 = client.fetch(8.3114, 80.4037, date(2023, 5, 1), date(2023, 5, 3), parameters=EXTENDED_PARAMETERS, reuse_grid_cell=True)
    ds2 = client.fetch(8.3150, 80.4050, date(2023, 5, 1), date(2023, 5, 3), parameters=EXTENDED_PARAMETERS, reuse_grid_cell=True)
    assert sess.calls == 1
    assert ds1.provenance["grid_cell_reused"] is False
    assert ds2.provenance["grid_cell_reused"] is True
    assert ds2.provenance["requested_coordinates"] == [80.4050, 8.3150]
    assert ds2.provenance["cached_request_coordinates"] == [80.4037, 8.3114]


def test_fao56_penman_monteith_and_daily_water_balance():
    demo = load_snapshot(ROOT / "data" / "demo_power.json")
    window = Window(5, 1, 8, 31)
    start, end = window.dates(2022)
    slice_df = demo.frame.loc[pd.Timestamp(start) : pd.Timestamp(end)].copy()
    slice_df.attrs.update(demo.frame.attrs)

    # Without wind speed, falls back to Hargreaves ET0
    et_hg = compute_fao56_penman_monteith_daily(slice_df, latitude=8.3114)
    assert (et_hg["et0_method"] == "fao56_hargreaves").all()
    assert et_hg["et0_mm"].notna().all()

    # With WS2M and PS, computes full FAO-56 Penman-Monteith ET0
    slice_pm = slice_df.copy()
    slice_pm["WS2M"] = 2.1
    slice_pm["PS"] = 100.2
    et_pm = compute_fao56_penman_monteith_daily(slice_pm, latitude=8.3114)
    assert (et_pm["et0_method"] == "fao56_penman_monteith").all()
    assert et_pm["et0_pm_mm"].notna().all()
    agromet = compute_daily_agromet_indices(slice_pm)
    assert agromet["et0_method"] == "fao56_penman_monteith"
    assert agromet["et0_pm_mm"] > 0

    kc_arr, stages = build_daily_kc_curve(120, kc_ini=0.35, kc_mid=1.15, kc_end=0.45)
    assert len(kc_arr) == 120 and len(stages) == 120
    assert stages[0] == "initial" and "mid_season" in stages and stages[-1] == "late_season"

    wb_upland = simulate_season_crop_water_balance(slice_pm, latitude=8.3114, is_paddy=False)
    wb_paddy = simulate_season_crop_water_balance(slice_pm, latitude=8.3114, is_paddy=True)
    assert wb_upland["valid"] and wb_paddy["valid"]
    assert wb_paddy["total_crop_water_need_mm"] > wb_upland["total_crop_water_need_mm"]
    assert wb_paddy["paddy_additional_water_mm"] > 0

    multi_wb = seasonal_water_balance_summary(demo.frame, window, latitude=8.3114)
    assert multi_wb["status"] == "verified" and multi_wb["valid_seasons"] >= 20


def test_extremes_and_stage_specific_risk():
    demo = load_snapshot(ROOT / "data" / "demo_power.json")
    window = Window(5, 1, 8, 31)
    unconfirmed = summarize_historical_extremes(demo.frame, window, sowing_date_confirmed=False)
    confirmed = summarize_historical_extremes(demo.frame, window, sowing_date_confirmed=True, reproductive_heat_threshold_c=32.0)

    assert unconfirmed["status"] == "verified"
    assert unconfirmed["stage_specific_mode"] == "general_seasonal_exposure_only"
    assert unconfirmed["reproductive_stage_summary"] is None
    assert confirmed["stage_specific_mode"] == "stage_resolved_from_confirmed_sowing"
    assert confirmed["reproductive_stage_summary"] is not None
    assert confirmed["reproductive_stage_summary"]["heat_days_max"] >= 0


def test_soil_normalization_interpretation_and_precedence():
    ph_norm = normalize_soilgrids_value("phh2o", 62)
    assert ph_norm["normalized_value"] == 6.2 and ph_norm["original_unit"] == "pH*10"
    bd_norm = normalize_soilgrids_value("bdod", 142)
    assert bd_norm["normalized_value"] == 1.42 and bd_norm["normalized_unit"] == "g/cm³"

    tex = classify_usda_texture(22.0, 41.0, 37.0)
    assert tex["texture_class"] == "loam"
    assert tex["compositional_closure_valid"] is True

    profile = interpret_soil_profile(
        {
            "0-5cm": {"phh2o": 6.1, "clay": 22.0, "sand": 42.0, "silt": 36.0, "bdod": 1.38, "soc": 18.0, "nitrogen": 1.5, "cec": 16.0, "cfvo": 5.0, "wv0033": 28.0, "wv1500": 12.0},
            "5-15cm": {"phh2o": 6.2, "clay": 24.0, "sand": 40.0, "silt": 36.0, "bdod": 1.42, "soc": 14.0, "nitrogen": 1.2, "cec": 17.0, "cfvo": 6.0, "wv0033": 29.0, "wv1500": 13.0},
            "15-30cm": {"phh2o": 6.3, "clay": 25.0, "sand": 39.0, "silt": 36.0, "bdod": 1.45, "soc": 10.0, "nitrogen": 0.9, "cec": 18.0, "cfvo": 8.0, "wv0033": 29.0, "wv1500": 13.5},
        }
    )
    assert profile["status"] == "verified"
    assert profile["topsoil_0_30cm"]["texture"]["texture_class"] == "loam"
    assert profile["topsoil_0_30cm"]["available_water_capacity_mm_m"] > 100
    assert profile["topsoil_0_30cm"]["salinity_ece_ds_m"] is None

    # Measured vs modelled soil precedence
    rec_both = reconcile_soil_evidence(6.8, {"value": 5.8, "q05": 5.2, "q95": 6.4, "source": "ISRIC SoilGrids 2.0"})
    assert rec_both["active_ph"] == 6.8
    assert rec_both["active_source_category"] == "farmer_measurement"
    assert rec_both["provisional_modelled_use"] is False
    assert rec_both["disagreement"]["meaningful_disagreement"] is True
    assert rec_both["disagreement"]["delta_ph"] == 1.0

    rec_model_only = reconcile_soil_evidence(None, {"value": 5.8, "source": "ISRIC SoilGrids 2.0"})
    assert rec_model_only["active_ph"] == 5.8
    assert rec_model_only["active_source_category"] == "modelled_estimate"
    assert rec_model_only["provisional_modelled_use"] is True

    # Offline WCS fallback, US-only USDA SDA, WoSIS offline, and CHIRPS latitude bounds
    wcs_offline = soil_profile_wcs(8.3114, 80.4037, offline=True)
    assert wcs_offline["status"] == "verified" and wcs_offline["value"] == 5.8
    assert usda_sda_soil(8.3114, 80.4037, "LK", offline=True)["status"] == "unavailable"
    assert usda_sda_soil(42.0308, -93.6319, "US", offline=True)["status"] == "verified"
    assert wosis_profiles(-1.25, 36.8, offline=True)["status"] == "verified"
    assert chirps_context(8.3114, 80.4037)["status"] == "verified"
    assert chirps_context(8.3114, 80.4037)["averaged_with_nasa_power"] is False
    assert chirps_context(64.5, 25.0)["status"] == "unavailable"


def test_expanded_gaez_polygon_and_calendar_matching():
    assert len(GAEZ_CROPS) == 24
    for crop_name in ("Wetland rice", "Gram", "Chickpea", "Cassava", "Sunflower", "Cotton", "Sugarcane", "Tomato"):
        res = gaez_point(8.3114, 80.4037, crop_name, "rainfed")
        assert res["status"] == "verified" and 1 <= res["class_code"] <= 8

    poly = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[80.38, 8.29], [80.43, 8.29], [80.43, 8.33], [80.38, 8.33], [80.38, 8.29]]],
        },
    }
    poly_res = gaez_polygon(poly, "Maize", "rainfed")
    assert poly_res["status"] == "verified"
    assert poly_res["sampled_points"] >= 5
    assert "10 km" in poly_res["resolution_note"]

    cal_rows = [
        {"crop": "Maize", "zone": "Lowland Dry Zone", "season": "Maha", "sow_from": "1 Oct", "sow_to": "30 Nov", "harvest_from": "1 Feb", "harvest_to": "31 Mar"}
    ]
    match_ok = match_crop_calendar(Window(10, 1, 2, 28), cal_rows, "Maize")
    match_conflict = match_crop_calendar(Window(5, 1, 8, 31), cal_rows, "Maize")
    assert match_ok["status"] == "matched" and match_ok["sowing_date_confirmed"] is True
    assert match_conflict["status"] == "conflict" and match_conflict["farmer_window_preserved"] is True


def test_expanded_knowledge_tables_and_catalogue():
    clear_cache()
    assert count_crops() >= 105
    assert len(growth_stages("maize")) == 4
    assert len(pest_context("maize")) >= 2
    assert len(cultivar_traits("mung_bean")) == 1
    assert len(soil_observations()) >= 3
    assert len(refresh_policies()) >= 5


def test_six_layer_evidence_combination_and_non_double_counting():
    ds = archived_history(request_parameters(8.3114, 80.4037, date(2001, 1, 1), date(2025, 12, 31)))
    farm = Farm(
        country="LK",
        latitude=8.3114,
        longitude=80.4037,
        windows=(Window(5, 1, 9, 30),),
        ph=6.4,
        drainage="well_drained",
        current="wheat",
    )
    cards = {c["id"]: c for c in find_options(farm, ds)}
    maize_card = cards["maize"]
    layers = build_evidence_layers(
        maize_card,
        farm,
        crop_identity=crop_by_id("maize"),
        previous_crop_identity=crop_by_id("wheat"),
        modelled_soil={"value": 5.8, "q05": 5.2, "q95": 6.5},
    )
    assert layers["classification_code"] in CLASSIFICATION_LABELS
    assert layers["layer_d_correlated_models"]["correlated_reanalysis_double_counted"] is False
    assert layers["layer_e_farmer_context"]["same_family_succession_warning"] is not None
    # Because wheat -> maize is Poaceae -> Poaceae, Layer F classifies as conditional compatibility
    assert layers["classification_code"] == "conditional_compatibility"


def test_global_rotation_planner_and_pest_context():
    ds = archived_history(request_parameters(-1.2921, 36.8219, date(2001, 1, 1), date(2025, 12, 31)))
    farm = Farm(
        country="KE",
        latitude=-1.2921,
        longitude=36.8219,
        windows=(Window(3, 1, 6, 30), Window(10, 1, 1, 20)),
        ph=6.4,
        drainage="well_drained",
        irrigation="reliable",
        irrigation_mm=300.0,
        rain_fraction=0.7,
    )
    plans = plan_global_rotations(farm, ds, candidate_crop_ids=["wheat", "dry_pea", "sugarcane"])
    assert plans
    by_id = {p["id"]: p for p in plans}
    assert by_id["wheat_then_dry_pea"]["overall_status"] == "complementary"
    assert by_id["wheat_then_wheat"]["overall_status"] == "caution"
    assert by_id["sugarcane_then_wheat"]["overall_status"] == "blocked"

    pest = evaluate_crop_pest_context("maize", ds.frame, farm.windows[0])
    assert pest["status"] == "verified"
    assert pest["chemical_prescription_included"] is False
    assert pest["outbreak_probability_predicted"] is False


def test_validation_ablation_aquacrop_prototype_and_refresh_governance():
    demo = load_snapshot(ROOT / "data" / "demo_power.json")
    slice_df = demo.frame.loc["2022-05-01":"2022-08-31"].copy()
    slice_df.attrs.update(demo.frame.attrs)

    sim = run_aquacrop_water_driven_prototype(slice_df, "maize", latitude=8.3114)
    assert sim["status"] == "simulated"
    assert sim["simulation"] is True
    assert sim["data_category"] == "hypothetical_simulation"
    assert sim["calibrated_to_farm"] is False
    assert sim["used_in_primary_screening"] is False

    stress = evaluate_missing_data_stress("nairobi_kenya")
    assert stress["conservative_fallback_verified"] is True

    holdout = evaluate_temporal_holdout(station_limit=3)
    assert holdout["stations_evaluated"] == 3
    assert 0.0 <= holdout["overall_temporal_status_agreement_rate"] <= 1.0

    ablation = run_ablation_study(station_limit=3)
    assert len(ablation["variants"]) == 5

    gov = evaluate_refresh_governance(date(2026, 11, 9))
    assert gov["status"] == "healthy"
    assert gov["gaez_archive"]["verified_files"] == 48
    assert gov["nasa_station_archives"]["verified_stations"] == 34


