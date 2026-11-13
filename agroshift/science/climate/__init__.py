"""Climate, meteorological aggregation, and NASA POWER integration package."""
from __future__ import annotations

from agroshift.science.climate.climate import (
    Window,
    aggregate,
    classify_anomalies,
    compute_daily_agromet_indices,
    dry_spell,
    mean_daylength_hours,
    season_samples,
    seasonal_summary,
)
from agroshift.science.climate.climate_insights import (
    climatology_for,
    crop_12month_sowing_matrix,
    crop_stage_water_demand,
    previous_crop_rotation_badge,
    seasonal_weather_risk_summary,
    site_summary,
    suggest_window,
)
from agroshift.science.climate.extremes import (
    analyze_season_extremes,
    summarize_historical_extremes,
)
from agroshift.science.climate.power import (
    ALLOWED_PARAMETERS,
    EXTENDED_PARAMETERS,
    PARAMETERS,
    DataError,
    Dataset,
    PowerClient,
    archived_history,
    coordinates,
    load_snapshot,
    parse_payload,
    power_grid_cell,
    request_parameters,
    unpack,
)

__all__ = [
    "ALLOWED_PARAMETERS",
    "DataError",
    "Dataset",
    "EXTENDED_PARAMETERS",
    "PARAMETERS",
    "PowerClient",
    "Window",
    "aggregate",
    "analyze_season_extremes",
    "archived_history",
    "classify_anomalies",
    "climatology_for",
    "compute_daily_agromet_indices",
    "coordinates",
    "crop_12month_sowing_matrix",
    "crop_stage_water_demand",
    "dry_spell",
    "load_snapshot",
    "mean_daylength_hours",
    "parse_payload",
    "power_grid_cell",
    "previous_crop_rotation_badge",
    "request_parameters",
    "season_samples",
    "seasonal_summary",
    "seasonal_weather_risk_summary",
    "site_summary",
    "suggest_window",
    "summarize_historical_extremes",
    "unpack",
]
