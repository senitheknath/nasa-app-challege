"""Smart Field Auto-Fill Engine.

Extracts objective environmental observations (NASA POWER, SoilGrids, Copernicus DEM)
to populate the farmer setup wizard without guesswork, while keeping every field
transparently editable and attributed.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from typing import Any

from ..identity.farm_records import polygon_area_hectares
from agroshift.monitoring.processors import soil_context, terrain_grid_context
from agroshift.earth_data.cache import get_cached, set_cached
from agroshift.earth_data.geometry import normalize_boundary, resolve_geometry


def _compute_area_item(norm_boundary: Any, area_ha: float | None) -> dict[str, Any]:
    """Compute field area metadata from drawn polygon or user-supplied hectares."""
    calc_area_ha = polygon_area_hectares(norm_boundary) if norm_boundary else None
    if calc_area_ha is not None:
        return {
            "value": round(calc_area_ha, 2),
            "acres": round(calc_area_ha * 2.47105, 2),
            "unit": "hectares",
            "source": "Geodetic area calculated from drawn field boundary",
            "confidence": "measured_polygon",
            "can_override": True,
        }
    if area_ha is not None and float(area_ha) > 0:
        val_ha = round(float(area_ha), 2)
        return {
            "value": val_ha,
            "acres": round(val_ha * 2.47105, 2),
            "unit": "hectares",
            "source": "User-supplied field area",
            "confidence": "user_supplied",
            "can_override": True,
        }
    return {
        "value": None,
        "acres": None,
        "unit": "hectares",
        "source": "No boundary drawn; enter field size manually or draw polygon on map",
        "confidence": "unmeasured",
        "can_override": True,
    }


def _compute_climate_item(dataset: Any) -> dict[str, Any]:
    """Extract seasonal climate & soil moisture carryover from a NASA POWER dataset."""
    climate_item: dict[str, Any] = {
        "seasonal_rainfall_mm": None,
        "temperature_mean_c": None,
        "root_zone_wetness": None,
        "topsoil_wetness": None,
        "source": "NASA POWER 25-yr agroclimatology archive",
        "confidence": "historical_archive",
        "can_override": True,
    }

    if dataset is not None and hasattr(dataset, "frame") and not dataset.frame.empty:
        df = dataset.frame
        if "PRECTOTCORR" in df.columns:
            annual_rain = df.groupby(df.index.year)["PRECTOTCORR"].sum()
            climate_item["seasonal_rainfall_mm"] = round(float(annual_rain.median()), 1)
        if "T2M" in df.columns:
            climate_item["temperature_mean_c"] = round(float(df["T2M"].mean()), 1)
        if "GWETROOT" in df.columns:
            climate_item["root_zone_wetness"] = round(float(df["GWETROOT"].median()), 2)
        if "GWETTOP" in df.columns:
            climate_item["topsoil_wetness"] = round(float(df["GWETTOP"].median()), 2)
    return climate_item


def derive_field_autofill(
    latitude: float,
    longitude: float,
    country: str = "LK",
    *,
    boundary: Any = None,
    area_ha: float | None = None,
    dataset: Any = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Derive non-fabricated initial farm parameters from verified Earth observations."""
    soil_geom = resolve_geometry("soil_grids", latitude, longitude, boundary=boundary, area_ha=area_ha)
    terrain_geom = resolve_geometry("terrain_dem", latitude, longitude, boundary=boundary, area_ha=area_ha)
    norm_boundary = terrain_geom["polygon"] or normalize_boundary(boundary)
    cache_type = f"field_autofill:{terrain_geom['cache_suffix']}"
    cached = get_cached(cache_type, latitude, longitude)
    if cached and not offline and isinstance(cached.get("data"), dict):
        data = deepcopy(cached["data"])
        if isinstance(data.get("location"), dict):
            data["location"]["country"] = country.upper()
        if isinstance(data.get("autofill"), dict):
            data["autofill"]["area_ha"] = _compute_area_item(norm_boundary, area_ha)
            if dataset is not None and hasattr(dataset, "frame") and not dataset.frame.empty:
                data["autofill"]["climate"] = _compute_climate_item(dataset)
        return data

    # 1 & 2. Fetch Soil pH (ISRIC SoilGrids 2.0) & Copernicus DEM terrain grid concurrently
    with ThreadPoolExecutor(max_workers=2) as pool:
        soil_fut = pool.submit(soil_context, latitude, longitude, offline=offline)
        terrain_fut = pool.submit(terrain_grid_context, terrain_geom["points"], offline=offline)
        soil_res = soil_fut.result()
        terrain_res = terrain_fut.result()

    ph_val = soil_res.get("value")
    ph_source = (
        "ISRIC SoilGrids 2.0 (modelled mean pH in water, 0–5 cm depth)"
        if ph_val is not None
        else "SoilGrids unavailable; enter measured pH or leave blank"
    )

    terrain_val = terrain_res.get("value") if isinstance(terrain_res.get("value"), dict) else terrain_res
    drainage_val = terrain_val.get("suggested_drainage_prior") if isinstance(terrain_val, dict) else None
    slope_pct = terrain_val.get("regional_slope_pct") if isinstance(terrain_val, dict) else None
    elev_m = terrain_val.get("elevation_m") if isinstance(terrain_val, dict) else None
    elev_min_m = terrain_val.get("elevation_min_m") if isinstance(terrain_val, dict) else None
    elev_max_m = terrain_val.get("elevation_max_m") if isinstance(terrain_val, dict) else None
    sample_points = terrain_val.get("sample_points", 1) if isinstance(terrain_val, dict) else 1

    # Never fabricate "well_drained" if Copernicus DEM is unreachable
    if not drainage_val:
        drainage_val = "unknown"
        drainage_source = "Copernicus DEM unavailable; verify if field experiences waterlogging or ponding"
    else:
        drainage_source = f"Copernicus DEM 90 m (elevation {elev_m} m, slope {slope_pct}%)"

    # 3. Field Area (from GeoJSON/UI polygon or explicit area_ha)
    area_item = _compute_area_item(norm_boundary, area_ha)

    # 4. Seasonal Climate & Soil Moisture Carryover (NASA POWER)
    climate_item = _compute_climate_item(dataset)

    result = {
        "location": {
            "country": country.upper(),
            "latitude": round(float(latitude), 5),
            "longitude": round(float(longitude), 5),
        },
        "autofill": {
            "ph": {
                "value": round(float(ph_val), 1) if ph_val is not None else None,
                "source": ph_source,
                "confidence": "modelled_surface" if ph_val is not None else "unavailable",
                "can_override": True,
            },
            "drainage": {
                "value": drainage_val,
                "slope_pct": slope_pct,
                "elevation_m": elev_m,
                "elevation_min_m": elev_min_m,
                "elevation_max_m": elev_max_m,
                "sample_points": sample_points,
                "precision_mode": terrain_geom["active_mode"],
                "source": drainage_source,
                "confidence": "inferred_terrain" if slope_pct is not None else "unavailable",
                "can_override": True,
            },
            "area_ha": area_item,
            "climate": climate_item,
        },
        "precision_policy": {
            "soil_grids": soil_geom["active_mode"],
            "terrain_dem": terrain_geom["active_mode"],
        },
    }

    if not offline:
        set_cached(cache_type, latitude, longitude, result, source="agroshift_autofill")

    return result
