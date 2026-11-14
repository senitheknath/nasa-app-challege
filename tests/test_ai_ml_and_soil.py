from __future__ import annotations

import pandas as pd

from agroshift.climate import Window, season_samples
from agroshift.decision import CRITERIA, Farm, assess
from agroshift.locations import load_history

DEFAULT_WEIGHTS = dict.fromkeys(CRITERIA, 25.0)
from agroshift.soil import reconcile_soil_evidence
from agroshift.soil_and_water import (
    IRRIGATION_SCHEDULE_PRESETS,
    LANDFORM_PRESETS,
    compute_general_screening_voi_guide,
    compute_saxton_rawls_hydraulics,
    compute_uncertainty_narrowing_guide,
    fetch_soil_profile,
    simulate_crop_water_and_thermal_physics,
)


def test_soil_profile_and_saxton_rawls_hydraulics():
    soil = fetch_soil_profile(8.3114, 80.4037, allow_network=False)
    assert "Anuradhapura" in soil["region_name"] or "Sri Lanka" in soil["region_name"]
    assert 5.5 <= soil["ph_median"] <= 7.2
    assert soil["hydraulics"]["awc_mm_per_m"] > 80.0

    hyd = compute_saxton_rawls_hydraulics(52.0, 26.0, 14.0)
    assert hyd["field_capacity_vol_pct"] > hyd["wilting_point_vol_pct"]
    assert hyd["awc_mm_per_m"] > 70.0

    reconciled_prior = reconcile_soil_evidence(None, {"value": soil["ph_median"]})
    assert reconciled_prior["active_source_category"] == "modelled_estimate"
    assert reconciled_prior["measured"]["present"] is False

    reconciled_measured = reconcile_soil_evidence(6.3, {"value": soil["ph_median"]})
    assert reconciled_measured["active_source_category"] == "farmer_measurement"
    assert reconciled_measured["active_ph"] == 6.3


def test_landform_and_irrigation_translators():
    assert LANDFORM_PRESETS["bunded_paddy"]["rain_fraction"] >= 0.70
    assert LANDFORM_PRESETS["sloped_rainfed"]["rain_fraction"] < 0.50
    assert IRRIGATION_SCHEDULE_PRESETS["agro_well_weekly"]["irrigation_mm"] == 180.0


def _anuradhapura_dataset():
    return load_history(8.3114, 80.4037)


def test_fao56_daily_root_zone_and_flowering_stress():
    ds = _anuradhapura_dataset()
    farm = Farm(
        latitude=8.3114,
        longitude=80.4037,
        current="rice",
        irrigation="supplemental",
        irrigation_mm=180.0,
        rain_fraction=0.60,
        drainage="well_drained",
        ph=6.3,
        pilot_confirmed=True,
    )
    sim = simulate_crop_water_and_thermal_physics(
        frame=ds.frame,
        window=Window(5, 1, 8, 31),
        crop_id="maize",
        farm=farm,
    )
    assert sim["available"] is True
    assert sim["etc_seasonal_median_mm"] > 0
    assert 0.0 <= sim["relative_et_sufficiency_pct"] <= 100.0
    assert sim["flowering_drought_days_median"] >= 0


def test_value_of_information_uncertainty_narrowing():
    ds = _anuradhapura_dataset()
    base_farm = Farm(
        latitude=8.3114,
        longitude=80.4037,
        current="rice",
        irrigation="unknown",
        irrigation_mm=None,
        rain_fraction=None,
        drainage="unknown",
        ph=None,
        pilot_confirmed=True,
    )
    voi = compute_uncertainty_narrowing_guide(ds.frame, base_farm, dict(DEFAULT_WEIGHTS))
    assert voi["available"] is True
    assert len(voi["actions"]) >= 3
    top_action = voi["actions"][0]
    assert top_action["impact_pts"] > 0

    full_farm = Farm(
        latitude=8.3114,
        longitude=80.4037,
        current="rice",
        irrigation="supplemental",
        irrigation_mm=180.0,
        rain_fraction=0.60,
        drainage="well_drained",
        ph=6.3,
        pilot_confirmed=True,
    )
    voi_full = compute_uncertainty_narrowing_guide(ds.frame, full_farm, dict(DEFAULT_WEIGHTS))
    assert voi_full["interval_precision_pct"] > voi["interval_precision_pct"]



def test_phase1_nrmc_aer_scs_rain_polygon_area_and_wfp_prices():
    from agroshift.farm_records import polygon_area_hectares
    from agroshift.soil_and_water import (
        compute_scs_usable_rain_fraction,
        detect_sri_lanka_aer,
        market_price_context,
    )

    aer = detect_sri_lanka_aer(8.3114, 80.4037)
    assert aer["in_sri_lanka"] is True
    assert "DL1" in aer["aer_code"]
    assert aer["is_lowland_dry_or_intermediate"] is True
    assert "Reddish Brown Earths" in aer["great_soil_group"]

    hills = detect_sri_lanka_aer(6.97, 80.78)
    assert hills["in_sri_lanka"] is True
    assert hills["is_lowland_dry_or_intermediate"] is False

    scs_bunded = compute_scs_usable_rain_fraction(slope_pct=1.2, bund_mode="bunded_basin", soil_type="sandy loam")
    scs_steep = compute_scs_usable_rain_fraction(slope_pct=9.5, bund_mode="unbunded", soil_type="clay")
    assert scs_bunded["rain_fraction"] > scs_steep["rain_fraction"]

    # ~100m x 100m square near equator (~1.0 ha)
    d = 0.00090
    poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [80.4000, 8.3100],
                [80.4000 + d, 8.3100],
                [80.4000 + d, 8.3100 + d],
                [80.4000, 8.3100 + d],
                [80.4000, 8.3100],
            ]
        ],
    }
    ha = polygon_area_hectares(poly)
    assert ha is not None and 0.8 <= ha <= 1.2

    wfp = market_price_context("LK")
    assert wfp["status"] == "verified"
    assert len(wfp["value"]) >= 5


def test_multilingual_nlp_intake_and_satellite_contexts():
    from agroshift.soil_and_water import (
        format_crop_with_local_name,
        parse_natural_language_farm_description,
        wapor_water_productivity_context,
        worldcereal_cropland_context,
    )

    label_lk = format_crop_with_local_name("rice", "Rice", "LK")
    assert "වී" in label_lk and "நெல்" in label_lk
    assert format_crop_with_local_name("rice", "Rice", "KE") == "Rice"

    parsed = parse_natural_language_farm_description(
        "2.5 acres bunded kumbura near Anuradhapura, grew wee last season, tank water 3 turns, clay loam soil, pH 6.2"
    )
    assert parsed["detected_count"] >= 6
    ext = parsed["extracted"]
    assert ext["area_ha"] == 1.01
    assert ext["ph"] == 6.2
    assert ext["soil_type"] == "clay loam"
    assert ext["drainage"] == "waterlogged"
    assert ext["rain_fraction"] == 0.72
    assert ext["irrigation"] == "supplemental"
    assert ext["irrigation_mm"] == 165.0
    assert ext["current"] == "rice"

    wapor = wapor_water_productivity_context(8.3114, 80.4037)
    assert wapor["status"] == "verified"
    assert wapor["value"]["annual_actual_et_aeti_mm"] > 500

    wc = worldcereal_cropland_context(8.3114, 80.4037)
    assert wc["status"] == "verified"
    assert wc["value"]["Detected Irrigation Regime Prior"] == "supplemental"


