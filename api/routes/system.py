"""System health, presets, and spatial GeoCache management routes."""
from __future__ import annotations

from dataclasses import asdict

import pycountry
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from agroshift.config import load_platform_config
from agroshift.presets import AREA_PRESETS, DEMO_SCENARIOS, LOCATION_PRESETS, SEASON_TEMPLATES
from agroshift.decision import CRITERIA
from agroshift.earth_data import DEFAULT_DB_PATH, get_connection, set_cached
from agroshift.knowledge import clear_cache, count_crops, crop_categories, knowledge_status
from agroshift.locations import stations
from agroshift.providers import GAEZ_SCALE

from api.deps import _DATASET_CACHE, _DATASET_LOCK, json_response


async def health(_request: Request) -> Response:
    """Service health check and active knowledge database status."""
    status = await run_in_threadpool(knowledge_status)
    return json_response({"status": "ok", "knowledge": status})


async def presets(_request: Request) -> Response:
    """Fetch reference presets (countries, weather stations, season templates, GAEZ scale)."""
    def _build():
        countries = sorted(
            [{"code": c.alpha_2, "name": c.name} for c in pycountry.countries],
            key=lambda item: item["name"],
        )
        station_list = [
            {"id": key, "country": cc, "latitude": lat, "longitude": lon}
            for key, (cc, lat, lon) in stations().items()
        ]
        loc_presets = [
            {"id": k, **v}
            for k, v in LOCATION_PRESETS.items()
            if v.get("latitude") is not None and v.get("longitude") is not None
        ]
        seasons = [
            {
                "id": k,
                "label": v["label"],
                "windows": [asdict(w) for w in v["windows"]],
            }
            for k, v in SEASON_TEMPLATES.items()
        ]
        scenarios = [
            {
                "id": k,
                "title": v["title"],
                "summary": v["summary"],
                "farm": asdict(v["farm"]),
            }
            for k, v in DEMO_SCENARIOS.items()
        ]
        return {
            "countries": countries,
            "stations": station_list,
            "location_presets": loc_presets,
            "season_templates": seasons,
            "area_presets": AREA_PRESETS,
            "demo_scenarios": scenarios,
            "categories": crop_categories(),
            "gaez_scale": [
                {"label": label, "bg": bg, "fg": fg}
                for label, bg, fg in GAEZ_SCALE
            ],
            "criteria": list(CRITERIA),
        }

    return json_response(await run_in_threadpool(_build))


async def cache_status(_request: Request) -> Response:
    """Inspect spatial GeoCache, memory climate cache, and knowledge database status."""
    try:
        def _run():
            geo_stats = {}
            db_size_kb = 0.0
            total_cells = 0
            if DEFAULT_DB_PATH.exists():
                db_size_kb = round(DEFAULT_DB_PATH.stat().st_size / 1024, 1)
                with get_connection() as conn:
                    rows = conn.execute(
                        "SELECT data_type, count(*) as count FROM geo_cache GROUP BY data_type"
                    ).fetchall()
                    for r in rows:
                        geo_stats[r["data_type"]] = r["count"]
                    row = conn.execute("SELECT count(*) FROM geo_cache").fetchone()
                    total_cells = row[0] if row else 0

            with _DATASET_LOCK:
                mem_climate_cells = len(_DATASET_CACHE)
                cached_coords = list(_DATASET_CACHE.keys())

            k_status = knowledge_status()
            total_crops_num = count_crops()

            return {
                "status": "active",
                "geocache": {
                    "db_path": str(DEFAULT_DB_PATH),
                    "db_size_kb": db_size_kb,
                    "total_entries": total_cells,
                    "by_type": geo_stats,
                },
                "memory_climate_cache": {
                    "total_cells": mem_climate_cells,
                    "cached_coords": cached_coords,
                },
                "knowledge_db": {
                    "backend": k_status.get("backend"),
                    "total_crops": total_crops_num,
                    "versions": k_status.get("versions"),
                },
            }

        return json_response(await run_in_threadpool(_run))
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=500)


async def cache_clear(request: Request) -> Response:
    """Clear memory climate datasets, SQLite GeoCache records, or knowledge LRU caches."""
    try:
        payload = {}
        try:
            payload = await request.json()
        except Exception:
            pass
        scope = str(payload.get("scope", "all")).lower()

        def _run():
            cleared = []
            if scope in ("all", "climate"):
                with _DATASET_LOCK:
                    count = len(_DATASET_CACHE)
                    _DATASET_CACHE.clear()
                    cleared.append(f"climate_memory ({count} cells)")

            if scope in ("all", "knowledge"):
                clear_cache()
                cleared.append("knowledge_lru_cache")

            if scope in ("all", "geocache"):
                target_type = payload.get("data_type")
                if DEFAULT_DB_PATH.exists():
                    with get_connection() as conn:
                        with conn:
                            if target_type:
                                res = conn.execute(
                                    "DELETE FROM geo_cache WHERE data_type = ?", (target_type,)
                                )
                                cleared.append(f"geocache:{target_type} ({res.rowcount} rows)")
                            else:
                                res = conn.execute("DELETE FROM geo_cache")
                                cleared.append(f"geocache:all ({res.rowcount} rows)")

            return {"status": "cleared", "scopes": cleared}

        return json_response(await run_in_threadpool(_run))
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=500)


async def cache_update(request: Request) -> Response:
    """Manually update or seed a spatial GeoCache observation (soil, DEM, overpass)."""
    try:
        payload = await request.json()
        data_type = str(payload["data_type"])
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        data = payload.get("payload") or {}
        source = str(payload.get("source", "manual_api_update"))
        precision = int(payload.get("precision", 3))

        def _run():
            set_cached(
                data_type,
                latitude,
                longitude,
                data,
                source=source,
                precision=precision,
            )
            return {
                "status": "updated",
                "data_type": data_type,
                "cell": [round(latitude, precision), round(longitude, precision)],
                "source": source,
            }

        return json_response(await run_in_threadpool(_run))
    except (KeyError, ValueError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=500)

async def system_config(_request: Request) -> Response:
    """Return active global platform configuration (spatial precision policies, cache, layers)."""
    return json_response({"config": load_platform_config()})


routes = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/system/presets", presets, methods=["GET"]),
    Route("/api/system/config", system_config, methods=["GET"]),
    Route("/api/cache/status", cache_status, methods=["GET"]),
    Route("/api/cache/clear", cache_clear, methods=["POST"]),
    Route("/api/cache/update", cache_update, methods=["POST"]),
]
