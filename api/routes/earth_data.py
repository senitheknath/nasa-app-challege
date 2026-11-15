"""Earth observation, climate telemetry, field autofill, and geospatial routes."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import inspect
import json
import threading
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

from agroshift.climate_insights import site_summary, suggest_window
from agroshift.decision import Farm
from agroshift.earth_data import (
    derive_field_autofill,
    fetch_satellite_overpasses,
    get_active_monitoring_layers,
    get_cached,
)
from agroshift.earth_data.geometry import resolve_geometry
from agroshift.farm_context import location_context
from agroshift.geography import search_places
from agroshift.locations import countries_at, country_map_view, country_regions
from agroshift.monitoring import build_3d_field_slab, evaluate_live_rotation_state
import agroshift.monitoring.engine_3d as _engine_3d
from agroshift.power import DataError
from agroshift.rotation import plan_global_rotations
from agroshift.science.climate.power import archived_history, request_parameters

from api.deps import (
    _DATASET_CACHE,
    _DATASET_LOCK,
    _align_dataset_coords,
    clean_json,
    get_dataset,
    json_response,
    parse_windows,
    resolve_farm_context,
    serialize_climatology,
)

_PREFETCH_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agroshift-prefetch")
_ROTATION_PLAN_CACHE: OrderedDict[tuple[Any, ...], list[dict[str, Any]]] = OrderedDict()
_ROTATION_PLAN_LOCK = threading.Lock()
_MAX_ROTATION_PLAN_CACHE = 32


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


def _parse_monitor_3d_params(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate common parameters for monitor_3d and monitor_3d_stream."""
    ctx = resolve_farm_context(request, payload)
    raw_stage = payload.get("stage") or request.query_params.get("stage") or "full"
    stage = str(raw_stage).strip().lower()
    if stage not in ("fast", "full"):
        raise ValueError("stage must be 'fast' or 'full'")

    raw_area = ctx["area_ha"]
    raw_ndvi = payload.get("observed_ndvi")
    raw_windows = payload.get("windows")
    start_date = payload.get("start_date") or (
        payload.get("farm").get("start_date") if isinstance(payload.get("farm"), dict) else None
    )
    return {
        "country": ctx["country"],
        "latitude": ctx["latitude"],
        "longitude": ctx["longitude"],
        "boundary": ctx["boundary"],
        "area_ha": float(raw_area) if raw_area is not None else None,
        "t_now_day": int(payload.get("t_now_day", 42)),
        "observed_ndvi": float(raw_ndvi) if raw_ndvi is not None else None,
        "offline": bool(payload.get("offline", False)),
        "refresh": bool(payload.get("refresh", False)),
        "weather_volatility": float(payload.get("weather_volatility", 0.18)),
        "windows": parse_windows(raw_windows, start_date=start_date),
        "max_sequences": int(payload.get("max_sequences", 6)),
        "irrigation": str(payload.get("irrigation") or "rainfed"),
        "stage": stage,
    }


def _get_warm_dataset_only(latitude: float, longitude: float) -> Any:
    """Return in-memory cached climate dataset if already warm, else None (< 0.1 ms)."""
    key = (round(float(latitude), 4), round(float(longitude), 4))
    with _DATASET_LOCK:
        ds = _DATASET_CACHE.get(key)
        if ds is not None:
            _DATASET_CACHE.move_to_end(key)
    return _align_dataset_coords(ds, latitude, longitude) if ds is not None else None


def _resolve_dataset_for_monitor(
    latitude: float,
    longitude: float,
    *,
    offline: bool,
    refresh: bool,
    fast_only: bool,
) -> Any:
    if fast_only:
        return _get_warm_dataset_only(latitude, longitude)
    if offline:
        req = request_parameters(latitude, longitude, date(2001, 1, 1), date(2025, 12, 31))
        return archived_history(req)
    try:
        return get_dataset(latitude, longitude, refresh=refresh)
    except DataError:
        return None


def _resolve_autofill_for_monitor(
    params: dict[str, Any],
    dataset: Any,
    *,
    fast_only: bool,
) -> dict[str, Any]:
    lat = params["latitude"]
    lon = params["longitude"]
    country = params["country"]
    boundary = params["boundary"]
    area_ha = params["area_ha"]
    offline = params["offline"]
    refresh = params["refresh"]

    if fast_only:
        if not refresh:
            terrain_geom = resolve_geometry("terrain_dem", lat, lon, boundary=boundary, area_ha=area_ha)
            cached = get_cached(f"field_autofill:{terrain_geom['cache_suffix']}", lat, lon)
            if cached and isinstance(cached.get("data"), dict):
                return cached["data"]
        return derive_field_autofill(
            lat,
            lon,
            country,
            boundary=boundary,
            area_ha=area_ha,
            dataset=dataset,
            offline=True,
        )

    return derive_field_autofill(
        lat,
        lon,
        country,
        boundary=boundary,
        area_ha=area_ha,
        dataset=dataset,
        offline=offline,
    )


def _rotation_cache_key(
    params: dict[str, Any],
    resolved_area: float | None,
    ph_val: float | None,
    drainage_val: str,
) -> tuple[Any, ...]:
    win_sig = tuple((w.start_month, w.start_day, w.end_month, w.end_day) for w in params["windows"])
    return (
        params["country"],
        round(float(params["latitude"]), 3),
        round(float(params["longitude"]), 3),
        round(float(resolved_area), 2) if resolved_area is not None else None,
        round(float(ph_val), 2) if ph_val is not None else None,
        drainage_val,
        params["irrigation"],
        win_sig,
        params["max_sequences"],
    )


def _compute_live_rotation_context(
    params: dict[str, Any],
    dataset: Any,
    af_res: dict[str, Any],
    *,
    fast_only: bool,
) -> dict[str, Any]:
    af = af_res.get("autofill", {})
    resolved_area = params["area_ha"] if params["area_ha"] is not None else (af.get("area_ha") or {}).get("value")
    ph_val = (af.get("ph") or {}).get("value")
    drainage_val = (af.get("drainage") or {}).get("value") or "well_drained"
    cache_key = _rotation_cache_key(params, resolved_area, ph_val, drainage_val)

    plans: list[dict[str, Any]] | None = None
    if not params["refresh"]:
        with _ROTATION_PLAN_LOCK:
            cached_plans = _ROTATION_PLAN_CACHE.get(cache_key)
            if cached_plans is not None:
                _ROTATION_PLAN_CACHE.move_to_end(cache_key)
                plans = list(cached_plans)

    if plans is None:
        if fast_only or dataset is None:
            plans = []
        else:
            try:
                farm = Farm(
                    country=params["country"],
                    latitude=params["latitude"],
                    longitude=params["longitude"],
                    area_ha=resolved_area,
                    windows=params["windows"],
                    ph=ph_val,
                    drainage=drainage_val,
                    irrigation=params["irrigation"],
                )
                plans = plan_global_rotations(farm, dataset, max_sequences=params["max_sequences"])
                with _ROTATION_PLAN_LOCK:
                    _ROTATION_PLAN_CACHE[cache_key] = list(plans)
                    _ROTATION_PLAN_CACHE.move_to_end(cache_key)
                    while len(_ROTATION_PLAN_CACHE) > _MAX_ROTATION_PLAN_CACHE:
                        _ROTATION_PLAN_CACHE.popitem(last=False)
            except (DataError, ValueError):
                plans = []

    live_rotation_monitor = evaluate_live_rotation_state(
        plans,
        t_now_day=params["t_now_day"],
        observed_ndvi=params["observed_ndvi"],
        weather_volatility=params["weather_volatility"],
    )

    plain = live_rotation_monitor.get("plain_rotations") or []
    observed_ndvi = params["observed_ndvi"]
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

    return {
        "resolved_area": resolved_area,
        "live_rotation_monitor": live_rotation_monitor,
        "active_root_depth_m": active_root_depth_m,
        "ndvi_current": ndvi_current,
        "ndvi_is_observed": observed_ndvi is not None,
    }


def _call_build_3d_field_slab(
    params: dict[str, Any],
    *,
    dataset: Any,
    resolved_area: float | None,
    active_root_depth_m: float,
    ndvi_current: float,
    stage: str,
    precomputed_autofill: dict[str, Any] | None = None,
    ndvi_is_observed: bool = False,
) -> dict[str, Any]:
    sig_params = inspect.signature(build_3d_field_slab).parameters
    kwargs: dict[str, Any] = {
        "boundary": params["boundary"],
        "area_ha": resolved_area,
        "dataset": dataset,
        "active_root_depth_m": active_root_depth_m,
        "ndvi_current": ndvi_current,
        "offline": params["offline"],
    }
    if "stage" in sig_params:
        kwargs["stage"] = stage
    if "precomputed_autofill" in sig_params and precomputed_autofill is not None:
        kwargs["precomputed_autofill"] = precomputed_autofill
    if "ndvi_is_observed" in sig_params:
        kwargs["ndvi_is_observed"] = ndvi_is_observed
    if "irrigation" in sig_params:
        kwargs["irrigation"] = params["irrigation"]
    return build_3d_field_slab(
        params["latitude"],
        params["longitude"],
        params["country"],
        **kwargs,
    )


async def monitor_3d(request: Request) -> Response:
    """Return unified 3D Field Slab and Live t > 0 Rotation Monitor."""
    try:
        payload = await request.json()
        params = _parse_monitor_3d_params(request, payload)
        fast_only = params["stage"] == "fast"

        def _run():
            ds = _resolve_dataset_for_monitor(
                params["latitude"],
                params["longitude"],
                offline=params["offline"],
                refresh=params["refresh"],
                fast_only=fast_only,
            )
            af_res = _resolve_autofill_for_monitor(params, ds, fast_only=fast_only)
            rot_ctx = _compute_live_rotation_context(params, ds, af_res, fast_only=fast_only)
            slab_3d = _call_build_3d_field_slab(
                params,
                dataset=ds,
                resolved_area=rot_ctx["resolved_area"],
                active_root_depth_m=rot_ctx["active_root_depth_m"],
                ndvi_current=rot_ctx["ndvi_current"],
                stage=params["stage"],
                precomputed_autofill=af_res,
                ndvi_is_observed=rot_ctx["ndvi_is_observed"],
            )
            return {
                "location": slab_3d["location"],
                "slab_3d": slab_3d,
                "live_rotation_monitor": rot_ctx["live_rotation_monitor"],
            }

        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def monitor_3d_stream(request: Request) -> Response:
    """Stream progressive 3D Field Slab fusion stages as NDJSON."""
    try:
        payload = await request.json()
        params = _parse_monitor_3d_params(request, payload)
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)

    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _produce() -> None:
        try:
            ds_fast = _resolve_dataset_for_monitor(
                params["latitude"],
                params["longitude"],
                offline=params["offline"],
                refresh=params["refresh"],
                fast_only=True,
            )
            af_fast = _resolve_autofill_for_monitor(params, ds_fast, fast_only=True)
            rot_ctx = _compute_live_rotation_context(params, ds_fast, af_fast, fast_only=True)

            iter_fn = getattr(_engine_3d, "iter_progressive_3d_field_slab", None)
            if callable(iter_fn):
                sig_params = inspect.signature(iter_fn).parameters
                iter_kwargs: dict[str, Any] = {
                    "boundary": params["boundary"],
                    "area_ha": rot_ctx["resolved_area"],
                    "dataset": ds_fast,
                    "active_root_depth_m": rot_ctx["active_root_depth_m"],
                    "ndvi_current": rot_ctx["ndvi_current"],
                    "offline": params["offline"],
                }
                if "precomputed_autofill" in sig_params:
                    iter_kwargs["precomputed_autofill"] = af_fast
                if "ndvi_is_observed" in sig_params:
                    iter_kwargs["ndvi_is_observed"] = rot_ctx["ndvi_is_observed"]
                if "irrigation" in sig_params:
                    iter_kwargs["irrigation"] = params["irrigation"]
                stage_iter = iter_fn(
                    params["latitude"],
                    params["longitude"],
                    params["country"],
                    **iter_kwargs,
                )
            else:
                def _fallback_iter():
                    yield _call_build_3d_field_slab(
                        params,
                        dataset=ds_fast,
                        resolved_area=rot_ctx["resolved_area"],
                        active_root_depth_m=rot_ctx["active_root_depth_m"],
                        ndvi_current=rot_ctx["ndvi_current"],
                        stage="fast",
                        precomputed_autofill=af_fast,
                        ndvi_is_observed=rot_ctx["ndvi_is_observed"],
                    )
                    ds_full = _resolve_dataset_for_monitor(
                        params["latitude"],
                        params["longitude"],
                        offline=params["offline"],
                        refresh=params["refresh"],
                        fast_only=False,
                    )
                    af_full = _resolve_autofill_for_monitor(params, ds_full, fast_only=False)
                    full_rot = _compute_live_rotation_context(params, ds_full, af_full, fast_only=False)
                    yield _call_build_3d_field_slab(
                        params,
                        dataset=ds_full,
                        resolved_area=full_rot["resolved_area"],
                        active_root_depth_m=full_rot["active_root_depth_m"],
                        ndvi_current=full_rot["ndvi_current"],
                        stage="full",
                        precomputed_autofill=af_full,
                        ndvi_is_observed=full_rot["ndvi_is_observed"],
                    )
                stage_iter = _fallback_iter()

            live_monitor = rot_ctx["live_rotation_monitor"]
            full_rot_future = None
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="agroshift-stream-rot") as rot_pool:
                for idx, slab in enumerate(stage_iter):
                    sf = slab.get("sensor_fusion") or {}
                    stage_name = str(
                        slab.get("fusion_stage")
                        or sf.get("fusion_stage")
                        or f"stage_{idx}"
                    )
                    if idx == 0:
                        def _resolve_full_rot() -> dict[str, Any]:
                            ds_full = _resolve_dataset_for_monitor(
                                params["latitude"],
                                params["longitude"],
                                offline=params["offline"],
                                refresh=params["refresh"],
                                fast_only=False,
                            )
                            af_full = _resolve_autofill_for_monitor(params, ds_full, fast_only=False)
                            return _compute_live_rotation_context(params, ds_full, af_full, fast_only=False)

                        full_rot_future = rot_pool.submit(_resolve_full_rot)
                    elif full_rot_future is not None:
                        if full_rot_future.done() or stage_name in ("stage_2_full_fusion", "full") or idx >= 2:
                            try:
                                live_monitor = full_rot_future.result()["live_rotation_monitor"]
                            except Exception:
                                pass

                    chunk_obj = clean_json(
                        {
                            "stage": stage_name,
                            "location": slab["location"],
                            "slab_3d": slab,
                            "live_rotation_monitor": live_monitor,
                        }
                    )
                    line = json.dumps(chunk_obj, separators=(",", ":"), ensure_ascii=False) + "\n"
                    loop.call_soon_threadsafe(queue.put_nowait, ("data", line))
        except Exception as exc:
            err_line = json.dumps({"error": str(exc)}, separators=(",", ":"), ensure_ascii=False) + "\n"
            loop.call_soon_threadsafe(queue.put_nowait, ("data", err_line))
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

    _PREFETCH_EXECUTOR.submit(_produce)

    async def _stream():
        while True:
            kind, item = await queue.get()
            if kind == "done":
                break
            yield item

    return StreamingResponse(
        _stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def prefetch(request: Request) -> Response:
    """Warm NASA POWER climate, autofill SoilGrids/DEM, and satellite overpass caches."""
    try:
        payload = await request.json()
        ctx = resolve_farm_context(request, payload)
        country = ctx["country"]
        latitude = ctx["latitude"]
        longitude = ctx["longitude"]
        boundary = ctx["boundary"]
        bbox = ctx["bbox"]
        raw_area = ctx["area_ha"]
        area_ha = float(raw_area) if raw_area is not None else None
        offline = bool(payload.get("offline", False))
        refresh = bool(payload.get("refresh", False))
        wait = bool(payload.get("wait", False))

        def _warm_caches() -> None:
            ds = None
            if offline:
                try:
                    req = request_parameters(latitude, longitude, date(2001, 1, 1), date(2025, 12, 31))
                    ds = archived_history(req)
                except Exception:
                    ds = None
            else:
                try:
                    ds = get_dataset(latitude, longitude, refresh=refresh)
                except Exception:
                    ds = None

            def _warm_autofill() -> None:
                try:
                    derive_field_autofill(
                        latitude,
                        longitude,
                        country,
                        boundary=boundary,
                        area_ha=area_ha,
                        dataset=ds,
                        offline=offline,
                    )
                except Exception:
                    pass

            def _warm_satellite() -> None:
                try:
                    fetch_satellite_overpasses(
                        latitude,
                        longitude,
                        boundary=boundary,
                        bbox=bbox,
                        area_ha=area_ha,
                        offline=offline,
                    )
                except Exception:
                    pass

            with ThreadPoolExecutor(max_workers=2) as pool:
                f_af = pool.submit(_warm_autofill)
                f_sat = pool.submit(_warm_satellite)
                f_af.result()
                f_sat.result()

        location_out = {"country": country, "latitude": latitude, "longitude": longitude}
        if wait:
            await run_in_threadpool(_warm_caches)
            return json_response({"status": "prefetch_completed", "location": location_out})

        _PREFETCH_EXECUTOR.submit(_warm_caches)
        return json_response({"status": "prefetch_scheduled", "location": location_out})
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


routes = [
    Route("/api/earth-data/autofill", autofill, methods=["POST"]),
    Route("/api/earth-data/satellite", satellite, methods=["POST"]),
    Route("/api/earth-data/climate", climate, methods=["POST"]),
    Route("/api/earth-data/monitor-3d", monitor_3d, methods=["POST"]),
    Route("/api/earth-data/monitor-3d/stream", monitor_3d_stream, methods=["POST"]),
    Route("/api/earth-data/prefetch", prefetch, methods=["POST"]),
    Route("/api/earth-data/layers", layers, methods=["GET"]),
    Route("/api/earth-data/places", places, methods=["GET"]),
]
