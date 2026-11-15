"""Earth observation, climate telemetry, field autofill, and geospatial routes."""
from __future__ import annotations

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from agroshift.climate_insights import site_summary, suggest_window
from agroshift.earth_data import (
    derive_field_autofill,
    fetch_satellite_overpasses,
    get_active_monitoring_layers,
)
from agroshift.farm_context import location_context
from agroshift.geography import search_places
from agroshift.locations import countries_at, country_map_view, country_regions
from agroshift.power import DataError

from api.deps import get_dataset, json_response, resolve_farm_context, serialize_climatology


async def autofill(request: Request) -> Response:
    """Derive smart field autofill (geodetic area, SoilGrids pH, Copernicus DEM drainage)."""
    try:
        payload = await request.json()
        ctx = resolve_farm_context(request, payload)
        country = ctx["country"]
        latitude = ctx["latitude"]
        longitude = ctx["longitude"]
        offline = bool(payload.get("offline", False))
        refresh = bool(payload.get("refresh", False))
        boundary = ctx["boundary"]
        raw_area = ctx["area_ha"]
        area_ha = float(raw_area) if raw_area is not None else None
        def _run():
            ds = get_dataset(latitude, longitude, refresh=refresh)
            result = derive_field_autofill(
                latitude,
                longitude,
                country,
                boundary=boundary,
                area_ha=area_ha,
                dataset=ds,
                offline=offline,
            )
            return {
                "location": {"country": country, "latitude": latitude, "longitude": longitude},
                "autofill": result["autofill"],
            }
        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def satellite(request: Request) -> Response:
    """Fetch NASA GIBS WMTS map layers and NASA CMR satellite overpass schedules."""
    try:
        payload = await request.json()
        ctx = resolve_farm_context(request, payload)
        latitude = ctx["latitude"]
        longitude = ctx["longitude"]
        offline = bool(payload.get("offline", False))
        boundary = ctx["boundary"]
        bbox = ctx["bbox"]
        raw_area = ctx["area_ha"]
        area_ha = float(raw_area) if raw_area is not None else None
        def _run():
            layers = get_active_monitoring_layers(latitude, longitude)
            overpasses = fetch_satellite_overpasses(
                latitude,
                longitude,
                boundary=boundary,
                bbox=bbox,
                area_ha=area_ha,
                offline=offline,
            )
            return {
                "location": {"latitude": latitude, "longitude": longitude},
                "layers": layers,
                "overpass_schedule": overpasses,
            }
        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def climate(request: Request) -> Response:
    """Fetch NASA POWER 25-year climate summary, 12-month climatology, and suggested window."""
    try:
        payload = await request.json()
        ctx = resolve_farm_context(request, payload)
        country = ctx["country"]
        latitude = ctx["latitude"]
        longitude = ctx["longitude"]
        offline = bool(payload.get("offline", False))
        refresh = bool(payload.get("refresh", False))

        def _run():
            ds = get_dataset(latitude, longitude, refresh=refresh)
            summary = site_summary(ds)
            clim_df = summary.pop("climatology")
            suggested = suggest_window(clim_df, summary.get("growing_period"))
            ctx = location_context(country, latitude, longitude, offline=offline)
            land_countries = countries_at(latitude, longitude)
            return {
                "location": {
                    "country": country,
                    "latitude": latitude,
                    "longitude": longitude,
                    "countries_at": land_countries,
                },
                "provenance": ds.provenance,
                "issues": ds.issues,
                "summary": {
                    **summary,
                    "climatology": serialize_climatology(clim_df),
                },
                "suggested_window": suggested,
                "context": ctx,
            }

        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def places(request: Request) -> Response:
    """Search global place names and retrieve country map views/regions."""
    q = (request.query_params.get("q") or "").strip()
    country = (request.query_params.get("country") or "").strip().upper()
    try:
        def _run():
            out = {}
            if country:
                out["map_view"] = country_map_view(country)
                out["regions"] = country_regions(country)
            if len(q) >= 2:
                out["results"] = search_places(q, country)
            else:
                out["results"] = []
            return out

        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError) as exc:
        return json_response({"error": str(exc)}, status_code=400)

async def layers(request: Request) -> Response:
    """Return global map overlay layers (NASA GIBS WMTS + ISRIC SoilGrids WMS)."""
    category = (request.query_params.get("category") or "").strip().lower()
    target_date = (request.query_params.get("date") or "").strip() or None
    all_layers = get_active_monitoring_layers(0.0, 0.0, target_date=target_date)
    if category:
        all_layers = [l for l in all_layers if l.get("category") == category]
    return json_response({"layers": all_layers, "count": len(all_layers)})


routes = [
    Route("/api/earth-data/autofill", autofill, methods=["POST"]),
    Route("/api/earth-data/satellite", satellite, methods=["POST"]),
    Route("/api/earth-data/climate", climate, methods=["POST"]),
    Route("/api/earth-data/layers", layers, methods=["GET"]),
    Route("/api/earth-data/places", places, methods=["GET"]),
]
