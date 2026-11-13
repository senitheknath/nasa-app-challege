"""Global platform configuration loader for adaptive spatial precision and monitoring."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "platform.json"

DEFAULT_PLATFORM_CONFIG: dict[str, Any] = {
    "spatial_precision": {
        "climate_power": {"mode": "centroid"},
        "soil_grids": {"mode": "sampled_grid", "min_area_ha": 5.0, "max_points": 5},
        "terrain_dem": {"mode": "sampled_grid", "min_area_ha": 1.0, "max_points": 9},
        "satellite_cmr": {
            "mode": "full_polygon",
            "max_vertices": 250,
            "fallback_mode": "bbox",
            "fallback_radius_deg": 0.1,
        },
    },
    "cache": {
        "geo_cache_ttl_hours": 168,
        "climate_lru_max_cells": 16,
    },
    "monitoring_layers": {
        "default_lag_days": 3,
        "enabled": [
            "smap_surface_soil_moisture",
            "modis_vegetation_vigor_ndvi",
            "gpm_imerg_precipitation_rate",
            "soilgrids_ph",
            "soilgrids_clay",
        ],
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


def load_platform_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load global platform configuration from JSON, merged over safe defaults."""
    env_path = os.getenv("AGROSHIFT_CONFIG_PATH", "").strip()
    target = Path(config_path or env_path or _DEFAULT_CONFIG_PATH)
    if target.exists():
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                return _deep_merge(DEFAULT_PLATFORM_CONFIG, loaded)
        except Exception:
            pass
    return deepcopy(DEFAULT_PLATFORM_CONFIG)


def get_precision_policy(usage: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the spatial precision policy dict for a subsystem (e.g. 'satellite_cmr')."""
    cfg = config or load_platform_config()
    policies = cfg.get("spatial_precision", {})
    return dict(policies.get(usage) or {"mode": "centroid"})
