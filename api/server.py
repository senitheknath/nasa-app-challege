"""Thin Starlette JSON API exposing AgroShift scientific engines without duplicating logic."""

from __future__ import annotations

import calendar
from collections import OrderedDict
from dataclasses import asdict, is_dataclass
import math
import threading
from typing import Any

import numpy as np
import pandas as pd
import pycountry
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from agroshift.identity import (
    authenticate_or_register,
    delete_user_farm,
    get_user_from_token,
    list_user_farms,
    save_user_farm,
)
from agroshift.assistant import AREA_PRESETS, DEMO_SCENARIOS, LOCATION_PRESETS, SEASON_TEMPLATES
from agroshift.climate_insights import (
    climatology_for,
    crop_12month_sowing_matrix,
    crop_stage_water_demand,
    previous_crop_rotation_badge,
    seasonal_weather_risk_summary,
    site_summary,
    suggest_window,
)
from agroshift.decision import CRITERIA, Farm, Window, assess, priority_sensitivity
from agroshift.evidence_combination import build_evidence_layers
from agroshift.farm_context import capabilities, location_context
from agroshift.finder_report import make_record, readable
from agroshift.earth_data import (
    derive_field_autofill,
    fetch_satellite_overpasses,
    get_active_monitoring_layers,
)
from agroshift.geography import pilot_scope, search_places
from agroshift.knowledge import (
    count_crops,
    crop_by_id,
    crop_categories,
    global_traits,
    knowledge_status,
    search_crops,
)
from agroshift.locations import (
    countries_at,
    country_map_view,
    country_regions,
    load_history,
    stations,
)
from agroshift.pests import evaluate_crop_pest_context
from agroshift.power import DataError
from agroshift.providers import GAEZ_CROP_ID_MAP, GAEZ_SCALE, gaez_point, gaez_polygon
from agroshift.rotation import plan_global_rotations
from agroshift.screening import find_options
from agroshift.water_balance import seasonal_water_balance_summary

_DATASET_CACHE: OrderedDict[tuple[float, float], Any] = OrderedDict()
_DATASET_LOCK = threading.Lock()


def _clean(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        f = float(value)
        return f if math.isfinite(f) else None
    if isinstance(value, pd.DataFrame):
        return [_clean(row) for row in value.to_dict(orient="records")]
    if isinstance(value, pd.Series):
        return _clean(value.to_dict())
    if is_dataclass(value) and not isinstance(value, type):
        return _clean(asdict(value))
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, set):
        return sorted(_clean(v) for v in value)
    return str(value)


def _json(data: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(_clean(data), status_code=status_code)


def _get_dataset(latitude: float, longitude: float, refresh: bool = False):
    key = (round(float(latitude), 4), round(float(longitude), 4))
    if not refresh:
        with _DATASET_LOCK:
            ds = _DATASET_CACHE.get(key)
            if ds is not None:
                _DATASET_CACHE.move_to_end(key)
                return ds
    ds = load_history(float(latitude), float(longitude), refresh=refresh)
    with _DATASET_LOCK:
        _DATASET_CACHE[key] = ds
        _DATASET_CACHE.move_to_end(key)
        while len(_DATASET_CACHE) > 16:
            _DATASET_CACHE.popitem(last=False)
    return ds


def _parse_windows(raw_windows: Any) -> tuple[Window, ...]:
    if not raw_windows:
        return (Window(5, 1, 8, 31),)
    parsed = []
    for item in raw_windows:
        parsed.append(
            Window(
                int(item["start_month"]),
                int(item["start_day"]),
                int(item["end_month"]),
                int(item["end_day"]),
            )
        )
    return tuple(parsed)


def _parse_farm(payload: dict[str, Any]) -> Farm:
    raw = payload.get("farm") if isinstance(payload.get("farm"), dict) else payload
    defaults = Farm()
    windows = _parse_windows(raw.get("windows"))
    ph = raw.get("ph")
    area_ha = raw.get("area_ha")
    irrigation_mm = raw.get("irrigation_mm")
    rain_fraction = raw.get("rain_fraction")
    return Farm(
        latitude=float(raw.get("latitude", defaults.latitude)),
        longitude=float(raw.get("longitude", defaults.longitude)),
        country=str(raw.get("country", defaults.country)).upper(),
        area_ha=float(area_ha) if area_ha is not None else None,
        previous=str(raw.get("previous") or "unknown"),
        current=str(raw.get("current") or "unknown"),
        baseline=tuple(raw.get("baseline") or defaults.baseline),
        allowed=tuple(raw.get("allowed") or defaults.allowed),
        drainage=str(raw.get("drainage") or "unknown"),
        ph=float(ph) if ph is not None else None,
        irrigation=str(raw.get("irrigation") or "unknown"),
        irrigation_mm=float(irrigation_mm) if irrigation_mm is not None else None,
        rain_fraction=float(rain_fraction) if rain_fraction is not None else None,
        windows=windows,
        pilot_confirmed=bool(raw.get("pilot_confirmed", False)),
        season_name=str(raw.get("season_name") or "Selected season"),
    )


def _parse_weights(raw_weights: Any) -> dict[str, float]:
    if not isinstance(raw_weights, dict):
        return {k: 1.0 for k in CRITERIA}
    return {k: float(raw_weights.get(k, 1.0)) for k in CRITERIA}


def _serialize_climatology(clim: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for month in range(1, 13):
        if month in clim.index:
            r = clim.loc[month]
            rows.append(
                {
                    "month": month,
                    "label": calendar.month_abbr[month],
                    "rain_mm": r.get("rain_mm"),
                    "et0_mm": r.get("et0_mm"),
                    "t_mean": r.get("t_mean"),
                    "t_min": r.get("t_min"),
                    "t_max": r.get("t_max"),
                }
            )
    return rows


async def health(_request: Request) -> Response:
    status = await run_in_threadpool(knowledge_status)
    return _json({"status": "ok", "knowledge": status})


async def bootstrap(_request: Request) -> Response:
    def _build():
        countries = sorted(
            [{"code": c.alpha_2, "name": c.name} for c in pycountry.countries],
            key=lambda item: item["name"],
        )
        station_list = [
            {"id": key, "country": cc, "latitude": lat, "longitude": lon}
            for key, (cc, lat, lon) in stations().items()
        ]
        presets = [
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
            "location_presets": presets,
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

    return _json(await run_in_threadpool(_build))


async def places(request: Request) -> Response:
    q = (request.query_params.get("q") or "").strip()
    country = (request.query_params.get("country") or "").strip().upper()
    try:
        def _run():
            out: dict[str, Any] = {}
            if country:
                out["map_view"] = country_map_view(country)
                out["regions"] = country_regions(country)
            if len(q) >= 2:
                out["results"] = search_places(q, country)
            else:
                out["results"] = []
            return out

        return _json(await run_in_threadpool(_run))
    except (DataError, ValueError) as exc:
        return _json({"error": str(exc)}, status_code=400)


async def site(request: Request) -> Response:
    try:
        payload = await request.json()
        country = str(payload.get("country", "LK")).upper()
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        offline = bool(payload.get("offline", False))
        refresh = bool(payload.get("refresh", False))
        boundary = payload.get("boundary")

        def _run():
            ds = _get_dataset(latitude, longitude, refresh=refresh)
            summary = site_summary(ds)
            clim_df = summary.pop("climatology")
            suggested = suggest_window(clim_df, summary.get("growing_period"))
            ctx = location_context(country, latitude, longitude, offline=offline)
            land_countries = countries_at(latitude, longitude)
            autofill_data = derive_field_autofill(
                latitude, longitude, country, boundary=boundary, dataset=ds, offline=offline
            )
            sat_layers = get_active_monitoring_layers(latitude, longitude)
            sat_overpasses = fetch_satellite_overpasses(
                latitude, longitude, boundary=boundary, offline=offline
            )
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
                    "climatology": _serialize_climatology(clim_df),
                },
                "suggested_window": suggested,
                "context": ctx,
                "autofill": autofill_data["autofill"],
                "satellite_monitoring": {
                    "layers": sat_layers,
                    "overpass_schedule": sat_overpasses,
                },
            }

        return _json(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return _json({"error": str(exc)}, status_code=400)


async def screen(request: Request) -> Response:
    try:
        payload = await request.json()
        farm = _parse_farm(payload)
        weights = _parse_weights(payload.get("weights"))
        include_matrix = bool(payload.get("include_sowing_matrix", True))

        def _run():
            ds = _get_dataset(farm.latitude, farm.longitude)
            cards = find_options(farm, ds, weights=weights)
            risk = seasonal_weather_risk_summary(ds, farm.windows[0])
            caps = capabilities(farm, ds, cards)
            matrix = crop_12month_sowing_matrix(ds, cards) if include_matrix else None
            return {
                "farm": asdict(farm),
                "pilot_scope": pilot_scope(
                    farm.latitude, farm.longitude, farm.country, farm.pilot_confirmed
                ),
                "capabilities": caps,
                "weather_risk": risk,
                "sowing_matrix": matrix,
                "cards": cards,
            }

        return _json(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return _json({"error": str(exc)}, status_code=400)


async def crop_details(request: Request) -> Response:
    crop_id = request.path_params["crop_id"]
    try:
        payload = await request.json()
        farm = _parse_farm(payload)
        weights = _parse_weights(payload.get("weights"))
        boundary = payload.get("boundary")
        offline = bool(payload.get("offline", False))

        def _run():
            ds = _get_dataset(farm.latitude, farm.longitude)
            cards = find_options(farm, ds, weights=weights)
            card = next((c for c in cards if c["id"] == crop_id), None)
            if card is None:
                raise DataError(f"Crop '{crop_id}' is not in the screened options for this farm.")

            crop_identity = crop_by_id(crop_id)
            prev_identity = (
                crop_by_id(farm.current)
                if farm.current not in (None, "unknown")
                else None
            )
            ctx = location_context(farm.country, farm.latitude, farm.longitude, offline=offline)
            extremes = seasonal_weather_risk_summary(ds, farm.windows[0])
            water_stages = crop_stage_water_demand(crop_id, ds, farm.windows[0])
            water_balance = seasonal_water_balance_summary(
                ds.frame,
                farm.windows[0],
                latitude=farm.latitude,
                is_paddy=(crop_id == "rice"),
            )

            # Calendar alignment lookup
            calendar_match = None
            cal = ctx.get("calendar") or {}
            if cal.get("status") == "verified" and isinstance(cal.get("value"), list):
                cname = (crop_identity or {}).get("name", "").casefold()
                for entry in cal["value"]:
                    if isinstance(entry, dict) and cname and cname in str(entry.get("crop", "")).casefold():
                        calendar_match = entry
                        break

            layers = build_evidence_layers(
                card,
                farm,
                crop_identity=crop_identity,
                previous_crop_identity=prev_identity,
                water_balance=water_balance,
                extremes=extremes,
                modelled_soil=ctx.get("soil"),
                calendar_match=calendar_match,
            )

            gaez_name = GAEZ_CROP_ID_MAP.get(crop_id)
            if gaez_name:
                if boundary:
                    gaez_rainfed = gaez_polygon(boundary, gaez_name, "rainfed")
                    gaez_irrigated = gaez_polygon(boundary, gaez_name, "irrigated")
                else:
                    gaez_rainfed = gaez_point(farm.latitude, farm.longitude, gaez_name, "rainfed")
                    gaez_irrigated = gaez_point(farm.latitude, farm.longitude, gaez_name, "irrigated")
            else:
                gaez_rainfed = {"status": "unavailable", "detail": "Not mapped to GAEZ v5."}
                gaez_irrigated = {"status": "unavailable", "detail": "Not mapped to GAEZ v5."}

            pest_ctx = evaluate_crop_pest_context(crop_id, ds.frame, farm.windows[0])
            rot_badge = previous_crop_rotation_badge(farm.current, crop_id)
            traits = [
                t
                for t in global_traits(crop_id)
                if t.get("review_status") == "reviewed"
            ]

            return {
                "card": card,
                "crop": crop_identity,
                "evidence_layers": layers,
                "water_stages": water_stages,
                "water_balance": water_balance,
                "extremes": extremes,
                "gaez": {
                    "mapped_crop": gaez_name,
                    "rainfed": gaez_rainfed,
                    "irrigated": gaez_irrigated,
                },
                "pest_context": pest_ctx,
                "rotation_badge": rot_badge,
                "traits": traits,
            }

        return _json(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return _json({"error": str(exc)}, status_code=400)


async def rotations(request: Request) -> Response:
    try:
        payload = await request.json()
        farm = _parse_farm(payload)
        weights = _parse_weights(payload.get("weights"))

        def _run():
            ds = _get_dataset(farm.latitude, farm.longitude)
            if pilot_scope(farm.latitude, farm.longitude, farm.country, farm.pilot_confirmed):
                rows = assess(ds.frame, farm, weights)
                sens = priority_sensitivity(rows, weights)
                return {
                    "mode": "regional",
                    "rows": rows,
                    "sensitivity": sens,
                }
            plans = plan_global_rotations(farm, ds)
            return {
                "mode": "global",
                "rows": plans,
                "sensitivity": [],
            }

        return _json(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return _json({"error": str(exc)}, status_code=400)


async def crops_catalogue(request: Request) -> Response:
    q = (request.query_params.get("q") or "").strip()
    category = (request.query_params.get("category") or "").strip() or None
    try:
        limit = int(request.query_params.get("limit", "50"))
        offset = int(request.query_params.get("offset", "0"))

        def _run():
            items = search_crops(query=q, limit=limit, offset=offset, category=category)
            total = count_crops(query=q, category=category)
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": items,
            }

        return _json(await run_in_threadpool(_run))
    except ValueError as exc:
        return _json({"error": str(exc)}, status_code=400)


async def report(request: Request) -> Response:
    fmt = (request.query_params.get("format") or "json").lower()
    try:
        payload = await request.json()
        farm = _parse_farm(payload)
        weights = _parse_weights(payload.get("weights"))
        offline = bool(payload.get("offline", False))

        def _run():
            ds = _get_dataset(farm.latitude, farm.longitude)
            cards = find_options(farm, ds, weights=weights)
            ctx = location_context(farm.country, farm.latitude, farm.longitude, offline=offline)
            record = make_record(ds, farm, cards, weights, context=ctx)
            if fmt == "html":
                return readable(record)
            return record

        result = await run_in_threadpool(_run)
        if fmt == "html":
            return HTMLResponse(result)
        return _json(result)
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return _json({"error": str(exc)}, status_code=400)


def _get_auth_user(request: Request) -> dict[str, Any]:
    auth_header = request.headers.get("Authorization") or ""
    user = get_user_from_token(auth_header)
    if not user:
        raise ValueError("Unauthorized: missing or invalid authorization token.")
    return user


async def auth_login(request: Request) -> Response:
    try:
        payload = await request.json()
        email = str(payload.get("email") or payload.get("username") or "")
        password = str(payload.get("password") or "")
        display_name = payload.get("display_name")
        res = await run_in_threadpool(authenticate_or_register, email, password, display_name)
        return _json(res)
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)


async def auth_me(request: Request) -> Response:
    try:
        user = _get_auth_user(request)
        return _json({"user": user})
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=401)


async def farms_list(request: Request) -> Response:
    try:
        user = _get_auth_user(request)
        farms = await run_in_threadpool(list_user_farms, user["id"])
        return _json({"farms": farms})
    except ValueError as exc:
        return _json({"error": str(exc)}, status_code=401)
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)


async def farms_save(request: Request) -> Response:
    try:
        user = _get_auth_user(request)
        payload = await request.json()
        name = str(payload.get("name") or "My Farm")
        farm_data = payload.get("farm") or payload
        boundary = payload.get("boundary")
        farm_id = payload.get("id")
        if "farm_id" in request.path_params:
            farm_id = int(request.path_params["farm_id"])
        saved = await run_in_threadpool(
            save_user_farm, user["id"], name, farm_data, boundary, farm_id
        )
        return _json({"farm": saved, "status": "saved"})
    except ValueError as exc:
        status_code = 401 if "Unauthorized" in str(exc) else 400
        return _json({"error": str(exc)}, status_code=status_code)
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)


async def farms_delete(request: Request) -> Response:
    try:
        user = _get_auth_user(request)
        farm_id = int(request.path_params["farm_id"])
        ok = await run_in_threadpool(delete_user_farm, user["id"], farm_id)
        if not ok:
            return _json({"error": "Farm not found"}, status_code=404)
        return _json({"status": "deleted", "id": farm_id})
    except ValueError as exc:
        status_code = 401 if "Unauthorized" in str(exc) else 400
        return _json({"error": str(exc)}, status_code=status_code)
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)

app = Starlette(
    debug=False,
    routes=[
        Route("/api/health", health, methods=["GET"]),
        Route("/api/bootstrap", bootstrap, methods=["GET"]),
        Route("/api/places", places, methods=["GET"]),
        Route("/api/site", site, methods=["POST"]),
        Route("/api/screen", screen, methods=["POST"]),
        Route("/api/crops/{crop_id}/details", crop_details, methods=["POST"]),
        Route("/api/rotations", rotations, methods=["POST"]),
        Route("/api/crops", crops_catalogue, methods=["GET"]),
        Route("/api/report", report, methods=["POST"]),
        Route("/api/auth/login", auth_login, methods=["POST"]),
        Route("/api/auth/register", auth_login, methods=["POST"]),
        Route("/api/auth/me", auth_me, methods=["GET"]),
        Route("/api/farms", farms_list, methods=["GET"]),
        Route("/api/farms", farms_save, methods=["POST"]),
        Route("/api/farms/{farm_id:int}", farms_save, methods=["PUT"]),
        Route("/api/farms/{farm_id:int}", farms_delete, methods=["DELETE"]),
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
