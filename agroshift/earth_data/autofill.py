"""Smart Field Auto-Fill Engine.

Extracts objective environmental observations (NASA POWER, SoilGrids, Copernicus DEM)
to populate the farmer setup wizard without guesswork, while keeping every field
transparently editable and attributed.
"""
from __future__ import annotations

from typing import Any

from ..farm_records import polygon_area_hectares
from ..providers import soil_context, terrain_context
from .cache import get_cached, set_cached


def derive_field_autofill(
    latitude: float,
    longitude: float,
    country: str = "LK",
    *,
    boundary: dict | None = None,
    dataset: Any = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Derive non-fabricated initial farm parameters from verified Earth observations."""
    cached = get_cached("field_autofill", latitude, longitude)
    if cached and not offline and boundary is None:
        return cached["data"]

    # 1. Soil pH (ISRIC SoilGrids 2.0 0-5 cm)
    soil_res = soil_context(latitude, longitude, offline=offline)
    ph_val = soil_res.get("value")
    ph_source = (
        "ISRIC SoilGrids 2.0 (modelled mean pH in water, 0–5 cm depth)"
        if ph_val is not None
        else "SoilGrids unavailable; enter measured pH or leave blank"
    )

    # 2. Terrain & Drainage Prior (Copernicus DEM 90m)
    terrain_res = terrain_context(latitude, longitude, offline=offline)
    drainage_val = terrain_res.get("suggested_drainage_prior")
    slope_pct = terrain_res.get("regional_slope_pct")
    elev_m = terrain_res.get("elevation_m")

    # Safe fallback if DEM is unreachable
    if not drainage_val:
        drainage_val = "well_drained"
        drainage_source = "Default prior; verify if field experiences waterlogging or ponding"
    else:
        drainage_source = f"Copernicus DEM 90 m (elevation {elev_m} m, slope {slope_pct}%)"

    # 3. Field Area (from GeoJSON polygon if present)
    area_ha = polygon_area_hectares(boundary) if boundary else None
    if area_ha is not None:
        area_item = {
            "value": round(area_ha, 2),
            "acres": round(area_ha * 2.47105, 2),
            "unit": "hectares",
            "source": "Geodetic area calculated from drawn field boundary",
            "confidence": "measured_polygon",
            "can_override": True,
        }
    else:
        area_item = {
            "value": None,
            "acres": None,
            "unit": "hectares",
            "source": "No boundary drawn; enter field size manually or draw polygon on map",
            "confidence": "unmeasured",
            "can_override": True,
        }

    # 4. Seasonal Climate & Soil Moisture Carryover (NASA POWER)
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
                "source": drainage_source,
                "confidence": "inferred_terrain" if slope_pct is not None else "heuristic_fallback",
                "can_override": True,
            },
            "area_ha": area_item,
            "climate": climate_item,
        },
    }

    if boundary is None:
        set_cached("field_autofill", latitude, longitude, result, source="agroshift_autofill")

    return result
