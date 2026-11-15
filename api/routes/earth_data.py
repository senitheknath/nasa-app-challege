"""Earth observation, climate telemetry, field autofill, and geospatial routes."""
from __future__ import annotations

from datetime import date

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from agroshift.climate_insights import site_summary, suggest_window
from agroshift.decision import Farm, Window
from agroshift.earth_data import (
    derive_field_autofill,
    fetch_satellite_overpasses,
    get_active_monitoring_layers,
)
from agroshift.farm_context import location_context
from agroshift.geography import search_places
from agroshift.locations import countries_at, country_map_view, country_regions
from agroshift.monitoring import build_3d_field_slab, evaluate_live_rotation_state
from agroshift.power import DataError
from agroshift.rotation import plan_global_rotations
from agroshift.science.climate.power import archived_history, request_parameters

from api.deps import (
    get_dataset,
    json_response,
    parse_windows,
    resolve_farm_context,
    serialize_climatology,
)


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
            try:
                ds = get_dataset(latitude, longitude, refresh=refresh)
            except DataError:
                ds = None
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


async def monitor_3d(request: Request) -> Response:
    """Return unified 3D Field Slab and Live t > 0 Rotation Monitor."""
    try:
        payload = await request.json()
        ctx = resolve_farm_context(request, payload)
        country = ctx["country"]
        latitude = ctx["latitude"]
        longitude = ctx["longitude"]
        boundary = ctx["boundary"]
        raw_area = ctx["area_ha"]
        area_ha = float(raw_area) if raw_area is not None else None
        t_now_day = int(payload.get("t_now_day", 42))
        raw_ndvi = payload.get("observed_ndvi")
        observed_ndvi = float(raw_ndvi) if raw_ndvi is not None else None
        offline = bool(payload.get("offline", False))
        refresh = bool(payload.get("refresh", False))
        weather_volatility = float(payload.get("weather_volatility", 0.18))
        raw_windows = payload.get("windows")
        start_date = payload.get("start_date") or (
            payload.get("farm").get("start_date") if isinstance(payload.get("farm"), dict) else None
        )
        windows = parse_windows(raw_windows, start_date=start_date)
        max_sequences = int(payload.get("max_sequences", 6))

        def _run():
            if offline:
                req = request_parameters(latitude, longitude, date(2001, 1, 1), date(2025, 12, 31))
                ds = archived_history(req)
            else:
                try:
                    ds = get_dataset(latitude, longitude, refresh=refresh)
                except DataError:
                    ds = None

            af_res = derive_field_autofill(
                latitude,
                longitude,
                country,
                boundary=boundary,
                area_ha=area_ha,
                dataset=ds,
                offline=offline,
            )
            af = af_res.get("autofill", {})
            resolved_area = area_ha if area_ha is not None else (af.get("area_ha") or {}).get("value")
            ph_val = (af.get("ph") or {}).get("value")
            drainage_val = (af.get("drainage") or {}).get("value") or "well_drained"

            if ds is not None:
                try:
                    farm = Farm(
                        country=country,
                        latitude=latitude,
                        longitude=longitude,
                        area_ha=resolved_area,
                        windows=windows,
                        ph=ph_val,
                        drainage=drainage_val,
                        irrigation=str(payload.get("irrigation") or "rainfed"),
                    )
                    plans = plan_global_rotations(farm, ds, max_sequences=max_sequences)
                except (DataError, ValueError):
                    plans = []
            else:
                plans = []

            live_rotation_monitor = evaluate_live_rotation_state(
                plans,
                t_now_day=t_now_day,
                observed_ndvi=observed_ndvi,
                weather_volatility=weather_volatility,
            )

            plain = live_rotation_monitor.get("plain_rotations") or []
            if plain:
                top_live = plain[0].get("live_state") or {}
                active_root_depth_m = float(top_live.get("active_root_depth_m", 0.45))
                ndvi_current = (
                    observed_ndvi
                    if observed_ndvi is not None
                    else float(top_live.get("expected_ndvi") or 0.58)
                )
            else:
                active_root_depth_m = 0.45
                ndvi_current = observed_ndvi if observed_ndvi is not None else 0.58

            slab_3d = build_3d_field_slab(
                latitude,
                longitude,
                country,
                boundary=boundary,
                area_ha=resolved_area,
                dataset=ds,
                active_root_depth_m=active_root_depth_m,
                ndvi_current=ndvi_current,
                offline=offline,
            )

            return {
                "location": slab_3d["location"],
                "slab_3d": slab_3d,
                "live_rotation_monitor": live_rotation_monitor,
            }

        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


routes = [
    Route("/api/earth-data/autofill", autofill, methods=["POST"]),
    Route("/api/earth-data/satellite", satellite, methods=["POST"]),
    Route("/api/earth-data/climate", climate, methods=["POST"]),
    Route("/api/earth-data/monitor-3d", monitor_3d, methods=["POST"]),
    Route("/api/earth-data/layers", layers, methods=["GET"]),
    Route("/api/earth-data/places", places, methods=["GET"]),
]
