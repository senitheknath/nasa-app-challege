"""Active satellite monitoring module for field boundaries and points.

Integrates:
1. NASA GIBS WMTS live tile endpoints (SMAP soil moisture, MODIS NDVI, GPM precipitation).
2. NASA CMR granule search for real overpasses (Harmonized Landsat 30m, ECOSTRESS 70m, SMAP 9km).
3. Local spatial caching via agroshift.geo_cache.
"""
from __future__ import annotations

import concurrent.futures
from datetime import date, datetime, timedelta, timezone
import json
from typing import Any, Callable
import urllib.parse
import urllib.request

from agroshift.config import load_platform_config
from agroshift.earth_data.cache import (
    get_cached,
    get_sensor_cached,
    set_cached,
    set_sensor_cached,
)
from agroshift.earth_data.geometry import normalize_boundary, resolve_geometry
from agroshift.monitoring.processors import compute_layer_update_frequencies
CMR_GRANULES_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
CDSE_STAC_URL = "https://stac.dataspace.copernicus.eu/v1/search"
EARTH_SEARCH_STAC_URL = "https://earth-search.aws.element84.com/v1/search"
GIBS_WMTS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"


def get_active_monitoring_layers(
    _latitude: float,
    _longitude: float,
    target_date: str | None = None,
) -> list[dict[str, Any]]:
    """Return configured NASA GIBS WMTS & ISRIC SoilGrids WMS layers ready for global map overlays."""
    cfg = load_platform_config()
    mon_cfg = cfg.get("monitoring_layers", {})
    lag_days = int(mon_cfg.get("default_lag_days", 3))
    enabled = set(mon_cfg.get("enabled") or [])

    if not target_date:
        ref_date = date.today() - timedelta(days=lag_days)
        obs_date = ref_date.isoformat()
    else:
        obs_date = str(target_date)

    all_layers = [
        {
            "id": "smap_surface_soil_moisture",
            "name": "SMAP Soil Moisture (9 km)",
            "category": "moisture",
            "observation_date": obs_date,
            "layer_type": "wmts",
            "max_native_zoom": 6,
            "wmts_layer": "SMAP_L3_Passive_Enhanced_Day_Soil_Moisture",
            "tile_url": f"{GIBS_WMTS_BASE}/SMAP_L3_Passive_Enhanced_Day_Soil_Moisture/default/{obs_date}/GoogleMapsCompatible_Level6/{{z}}/{{y}}/{{x}}.png",
            "unit": "cm³/cm³ (volumetric)",
            "resolution": "9 km",
            "source": "NASA NSIDC DAAC / SMAP Radiometer",
            "description": "Daily global surface soil moisture (0–5 cm depth) indicating field wetness and water stress.",
        },
        {
            "id": "modis_vegetation_vigor_ndvi",
            "name": "MODIS Vegetation Index (NDVI)",
            "category": "plant_state",
            "observation_date": obs_date,
            "layer_type": "wmts",
            "max_native_zoom": 9,
            "wmts_layer": "MODIS_Terra_NDVI_8Day",
            "tile_url": f"{GIBS_WMTS_BASE}/MODIS_Terra_NDVI_8Day/default/{obs_date}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.png",
            "unit": "NDVI (-0.2 to 1.0)",
            "resolution": "250 m",
            "source": "NASA LP DAAC / Terra MODIS",
            "description": "8-day normalized difference vegetation index showing crop canopy vigor and biomass density.",
        },
        {
            "id": "gpm_imerg_precipitation_rate",
            "name": "GPM IMERG Rain Rate",
            "category": "moisture",
            "observation_date": obs_date,
            "layer_type": "wmts",
            "max_native_zoom": 6,
            "wmts_layer": "IMERG_Precipitation_Rate",
            "tile_url": f"{GIBS_WMTS_BASE}/IMERG_Precipitation_Rate/default/{obs_date}/GoogleMapsCompatible_Level6/{{z}}/{{y}}/{{x}}.png",
            "unit": "mm/hr",
            "resolution": "10 km (0.1°)",
            "source": "NASA GES DISC / GPM Constellation",
            "description": "Near-real-time satellite precipitation rate tracking active rainstorms.",
        },
        {
            "id": "soilgrids_ph",
            "name": "SoilGrids Soil pH (0–5 cm)",
            "category": "soil",
            "observation_date": "2020-static",
            "layer_type": "wms",
            "wms_url": "https://maps.isric.org/mapserv?map=/map/phh2o.map",
            "wms_layers": "phh2o_0-5cm_mean",
            "unit": "pH (H₂O)",
            "resolution": "250 m",
            "source": "ISRIC SoilGrids 2.0",
            "description": "Global topsoil pH layer (0–5 cm) for overlaying soil acidity/alkalinity on the field map.",
        },
        {
            "id": "soilgrids_clay",
            "name": "SoilGrids Clay Content (0–5 cm)",
            "category": "soil",
            "observation_date": "2020-static",
            "layer_type": "wms",
            "wms_url": "https://maps.isric.org/mapserv?map=/map/clay.map",
            "wms_layers": "clay_0-5cm_mean",
            "unit": "g/kg",
            "resolution": "250 m",
            "source": "ISRIC SoilGrids 2.0",
            "description": "Global topsoil clay fraction (0–5 cm) for drainage and water-retention context.",
        },
    ]
    if enabled:
        return [layer for layer in all_layers if layer["id"] in enabled]
    return all_layers


def _extract_stac_browse_url(feature: dict[str, Any]) -> str | None:
    """Extract a thumbnail or preview URL from a STAC Item's assets or links."""
    assets = feature.get("assets")
    if isinstance(assets, dict):
        for key in ("thumbnail", "overview", "rendered_preview"):
            asset = assets.get(key)
            if isinstance(asset, dict) and asset.get("href"):
                return str(asset["href"])
    links = feature.get("links")
    if isinstance(links, list):
        for link in links:
            if (
                isinstance(link, dict)
                and str(link.get("rel", "")).lower() in {"thumbnail", "preview"}
                and link.get("href")
            ):
                return str(link["href"])
    return None


def _query_stac_collection(
    stac_url: str,
    coll_id: str,
    sensor_id: str,
    sensor_label: str,
    sensor_role: str,
    recurrence: str,
    bbox_coords: list[float],
    limit_per_sensor: int,
) -> list[dict[str, Any]]:
    """Query a STAC /search endpoint for a single collection and normalize matching items."""
    payload = json.dumps(
        {
            "collections": [coll_id],
            "bbox": bbox_coords,
            "limit": limit_per_sensor,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        stac_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/geo+json, application/json",
            "User-Agent": "AgroShift-SatelliteMonitor/1.0",
        },
        method="POST",
    )
    items: list[dict[str, Any]] = []
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, dict):
            return items
        features = data.get("features")
        if not isinstance(features, list):
            return items
        for feature in features:
            if (
                not isinstance(feature, dict)
                or not feature.get("id")
                or not isinstance(feature.get("properties"), dict)
            ):
                continue
            props = feature["properties"]
            acquired_at = props.get("datetime") or props.get("start_datetime") or ""
            cloud_cover = props.get("eo:cloud_cover")
            items.append(
                {
                    "sensor": sensor_id,
                    "label": sensor_label,
                    "role": sensor_role,
                    "recurrence": recurrence,
                    "granule_id": str(feature["id"]),
                    "acquired_at": str(acquired_at),
                    "cloud_cover_pct": float(cloud_cover) if cloud_cover is not None else None,
                    "browse_url": _extract_stac_browse_url(feature),
                    "status": "available",
                }
            )
    except Exception:
        return []
    return items


def _query_cmr_sensor(
    short_name: str,
    sensor_label: str,
    sensor_role: str,
    recurrence: str,
    bbox_str: str,
    cmr_polygon: str | None,
    active_mode: str,
    limit_per_sensor: int,
) -> list[dict[str, Any]]:
    """Query NASA CMR for a single sensor short_name and normalize matching granules."""
    params: dict[str, str] = {
        "short_name": short_name,
        "page_size": str(limit_per_sensor),
        "sort_key": "-start_date",
    }
    if cmr_polygon and active_mode == "full_polygon":
        params["polygon"] = cmr_polygon
    else:
        params["bounding_box"] = bbox_str
    url = f"{CMR_GRANULES_URL}?{urllib.parse.urlencode(params)}"
    items: list[dict[str, Any]] = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgroShift-SatelliteMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        entries = data.get("feed", {}).get("entry", [])
        for entry in entries:
            title = entry.get("title", "")
            start_time = entry.get("time_start", "")
            cloud_cover = entry.get("cloud_cover")
            browse_url = next(
                (
                    link.get("href")
                    for link in (entry.get("links") or [])
                    if isinstance(link, dict)
                    and "browse" in str(link.get("rel", "")).lower()
                    and link.get("href")
                ),
                None,
            )
            items.append(
                {
                    "sensor": short_name,
                    "label": sensor_label,
                    "role": sensor_role,
                    "recurrence": recurrence,
                    "granule_id": title,
                    "acquired_at": start_time,
                    "cloud_cover_pct": float(cloud_cover) if cloud_cover is not None else None,
                    "browse_url": browse_url,
                    "status": "available",
                }
            )
    except Exception:
        return []
    return items


def fetch_satellite_overpasses(
    latitude: float,
    longitude: float,
    *,
    boundary: Any = None,
    bbox: Any = None,
    area_ha: float | None = None,
    offline: bool = False,
    limit_per_sensor: int = 2,
    on_sensor_data: Callable[[str, list[dict[str, Any]]], None] | None = None,
) -> dict[str, Any]:
    """Query multi-provider STAC (CDSE + Earth-Search) and NASA CMR for Earth observation scenes."""
    geom = resolve_geometry(
        "satellite_cmr",
        latitude,
        longitude,
        boundary=boundary,
        bbox=bbox,
        area_ha=area_ha,
    )
    cache_type = f"satellite_overpass:{geom['cache_suffix']}"
    cached = get_cached(cache_type, latitude, longitude)
    if cached and not offline:
        data = dict(cached["data"])
        if "layer_update_frequencies" not in data:
            clouds = [
                a["cloud_cover_pct"]
                for a in data.get("acquisitions", [])
                if a.get("cloud_cover_pct") is not None
            ]
            avg_cloud = sum(clouds) / len(clouds) if clouds else 22.0
            data["layer_update_frequencies"] = compute_layer_update_frequencies(cloud_cover_pct=avg_cloud)
        if on_sensor_data is not None:
            by_sensor: dict[str, list[dict[str, Any]]] = {}
            for acq in data.get("acquisitions", []):
                s_id = str(acq.get("sensor") or "")
                if s_id:
                    by_sensor.setdefault(s_id, []).append(acq)
            for s_id, items in by_sensor.items():
                on_sensor_data(s_id, items)
        return data

    stac_sensors = [
        (
            CDSE_STAC_URL,
            "sentinel-2-l2a",
            "SENTINEL2_L2A",
            "Copernicus Sentinel-2 L2A (10 m)",
            "surface_reflectance_ndvi",
            "5 days",
        ),
        (
            CDSE_STAC_URL,
            "sentinel-1-grd",
            "SENTINEL1_GRD",
            "Copernicus Sentinel-1 C-Band SAR (10 m)",
            "cloud_piercing_radar_wetness",
            "6 days",
        ),
        (
            CDSE_STAC_URL,
            "sentinel-3-slstr-2-lst-nrt",
            "SENTINEL3_SLSTR",
            "Copernicus Sentinel-3 SLSTR Thermal (1 km)",
            "daily_regional_thermal_lst",
            "1 day",
        ),
        (
            EARTH_SEARCH_STAC_URL,
            "landsat-c2-l2",
            "LANDSAT_C2_L2",
            "Landsat 8/9 C2 L2 Optical+Thermal (30m/100m)",
            "surface_reflectance_and_thermal",
            "8 days",
        ),
        (
            EARTH_SEARCH_STAC_URL,
            "cop-dem-glo-30",
            "COP_DEM_GLO30",
            "Copernicus DEM GLO-30 (30 m)",
            "terrain_3d_elevation",
            "static",
        ),
    ]

    sensors = [
        ("HLSL30", "Harmonized Landsat Sentinel-2 (30 m)", "surface_reflectance_ndvi", "2–3 days"),
        ("ECO_L3T_JET", "ECOSTRESS Evapotranspiration (70 m)", "canopy_water_stress", "3–5 days"),
        ("SPL3SMP_E", "SMAP Enhanced Soil Moisture (9 km)", "root_zone_wetness", "1–2 days"),
    ]

    bbox_str = geom["bbox"]
    cmr_polygon = geom["cmr_polygon"]
    acquisitions: list[dict[str, Any]] = []

    if not offline:
        try:
            bbox_coords = [float(part.strip()) for part in bbox_str.split(",")]
        except ValueError:
            bbox_coords = []

        tasks: list[tuple[str, str, Callable[..., list[dict[str, Any]]], tuple[Any, ...]]] = []
        if len(bbox_coords) == 4:
            for stac_url, coll_id, sensor_id, sensor_label, sensor_role, recurrence in stac_sensors:
                tasks.append(
                    (
                        sensor_id,
                        "stac_api",
                        _query_stac_collection,
                        (
                            stac_url,
                            coll_id,
                            sensor_id,
                            sensor_label,
                            sensor_role,
                            recurrence,
                            bbox_coords,
                            limit_per_sensor,
                        ),
                    )
                )

        for short_name, sensor_label, sensor_role, recurrence in sensors:
            tasks.append(
                (
                    short_name,
                    "nasa_cmr_api",
                    _query_cmr_sensor,
                    (
                        short_name,
                        sensor_label,
                        sensor_role,
                        recurrence,
                        bbox_str,
                        cmr_polygon,
                        geom["active_mode"],
                        limit_per_sensor,
                    ),
                )
            )

        results_by_idx: dict[int, list[dict[str, Any]]] = {}
        pending: list[tuple[int, str, str, Callable[..., list[dict[str, Any]]], tuple[Any, ...]]] = []

        for idx, (sensor_id, source_tag, fn, args) in enumerate(tasks):
            cached_sensor = get_sensor_cached(sensor_id, latitude, longitude)
            if cached_sensor and isinstance(cached_sensor.get("data"), (list, dict)):
                raw_data = cached_sensor["data"]
                items = (
                    list(raw_data)
                    if isinstance(raw_data, list)
                    else list(raw_data.get("acquisitions") or [])
                )
                results_by_idx[idx] = items
                if on_sensor_data is not None:
                    on_sensor_data(sensor_id, items)
            else:
                pending.append((idx, sensor_id, source_tag, fn, args))

        if pending:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_map: dict[
                    concurrent.futures.Future[list[dict[str, Any]]],
                    tuple[int, str, str],
                ] = {
                    executor.submit(fn, *args): (idx, sensor_id, source_tag)
                    for idx, sensor_id, source_tag, fn, args in pending
                }
                for fut in concurrent.futures.as_completed(future_map):
                    idx, sensor_id, source_tag = future_map[fut]
                    try:
                        items = fut.result()
                    except Exception:
                        items = []
                    results_by_idx[idx] = items
                    if items:
                        set_sensor_cached(sensor_id, latitude, longitude, items, source=source_tag)
                    if on_sensor_data is not None:
                        on_sensor_data(sensor_id, items)

        for idx in range(len(tasks)):
            acquisitions.extend(results_by_idx.get(idx, []))

    # Never fabricate synthetic granule IDs or cloud cover if offline or CMR is unreachable
    cmr_status = "verified" if acquisitions else ("offline" if offline else "unavailable")
    clouds = [a["cloud_cover_pct"] for a in acquisitions if a.get("cloud_cover_pct") is not None]
    avg_cloud = sum(clouds) / len(clouds) if clouds else 22.0

    result = {
        "status": cmr_status,
        "precision_mode": geom["active_mode"],
        "polygon_hash": geom["polygon_hash"],
        "bounding_box": bbox_str,
        "acquisitions_count": len(acquisitions),
        "acquisitions": acquisitions,
        "layer_update_frequencies": compute_layer_update_frequencies(cloud_cover_pct=avg_cloud),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }

    # Cache result under precision-aware key only when real acquisitions were retrieved
    if acquisitions:
        set_cached(cache_type, latitude, longitude, result, source="nasa_cmr_api")
    return result
