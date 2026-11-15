"""Soil properties, FAO-56 crop water balance, and AquaCrop simulation package."""
from __future__ import annotations

from agroshift.science.soil_water.aquacrop_prototype import (
    run_aquacrop_water_driven_prototype,
)
from agroshift.science.soil_water.soil import (
    classify_usda_texture,
    interpret_soil_profile,
    normalize_soilgrids_value,
    reconcile_soil_evidence,
)
from agroshift.science.soil_water.soil_and_water import (
    IRRIGATION_SCHEDULE_PRESETS,
    LANDFORM_PRESETS,
    compute_general_screening_voi_guide,
    compute_scs_usable_rain_fraction,
    compute_uncertainty_narrowing_guide,
    detect_sri_lanka_aer,
    fetch_soil_profile,
    format_crop_with_local_name,
    market_price_context,
    parse_natural_language_farm_description,
    simulate_crop_water_and_thermal_physics,
    wapor_water_productivity_context,
)
from agroshift.science.soil_water.water_balance import (
    DEFAULT_STAGE_FRACTIONS,
    build_daily_kc_curve,
    compute_fao56_penman_monteith_daily,
    seasonal_water_balance_summary,
)

__all__ = [
    "DEFAULT_STAGE_FRACTIONS",
    "IRRIGATION_SCHEDULE_PRESETS",
    "LANDFORM_PRESETS",
    "build_daily_kc_curve",
    "classify_usda_texture",
    "compute_fao56_penman_monteith_daily",
    "compute_general_screening_voi_guide",
    "compute_scs_usable_rain_fraction",
    "compute_uncertainty_narrowing_guide",
    "detect_sri_lanka_aer",
    "fetch_soil_profile",
    "format_crop_with_local_name",
    "interpret_soil_profile",
    "market_price_context",
    "normalize_soilgrids_value",
    "parse_natural_language_farm_description",
    "reconcile_soil_evidence",
    "run_aquacrop_water_driven_prototype",
    "seasonal_water_balance_summary",
    "simulate_crop_water_and_thermal_physics",
    "wapor_water_productivity_context",
]
