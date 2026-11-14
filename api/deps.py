"""Shared dependencies, serialization helpers, and optional auth utilities for AgroShift API."""
from __future__ import annotations

import calendar
from collections import OrderedDict
from dataclasses import asdict, is_dataclass
import math
import threading
from typing import Any

import numpy as np
import pandas as pd
from starlette.requests import Request
from starlette.responses import JSONResponse

from agroshift.decision import CRITERIA, Farm, Window
from agroshift.identity import get_user_from_token, list_user_farms
from agroshift.locations import load_history

_DATASET_CACHE: OrderedDict[tuple[float, float], Any] = OrderedDict()
_DATASET_LOCK = threading.Lock()


def clean_json(value: Any) -> Any:
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
        return [clean_json(row) for row in value.to_dict(orient="records")]
    if isinstance(value, pd.Series):
        return clean_json(value.to_dict())
    if is_dataclass(value) and not isinstance(value, type):
        return clean_json(asdict(value))
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, set):
        return sorted(clean_json(v) for v in value)
    return str(value)


def json_response(data: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(clean_json(data), status_code=status_code)


def get_dataset(latitude: float, longitude: float, refresh: bool = False):
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


def parse_windows(raw_windows: Any) -> tuple[Window, ...]:
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


def parse_farm(payload: dict[str, Any]) -> Farm:
    raw = payload.get("farm") if isinstance(payload.get("farm"), dict) else payload
    defaults = Farm()
    windows = parse_windows(raw.get("windows"))
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


def parse_weights(raw_weights: Any) -> dict[str, float]:
    if not isinstance(raw_weights, dict):
        return {k: 1.0 for k in CRITERIA}
    return {k: float(raw_weights.get(k, 1.0)) for k in CRITERIA}


def serialize_climatology(clim: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for month in range(1, 13):
        if month in clim.index:
            r = clim.loc[month]
            rows.append(
                {
                    "month": month,
                    "label": calendar.month_abbr[month],
                    "rainfall_mm": r.get("rainfall_mm"),
                    "temperature_c": r.get("temperature_c"),
                    "t_min": r.get("t_min"),
                    "t_max": r.get("t_max"),
                }
            )
    return rows


def get_optional_auth_user(request: Request) -> dict[str, Any] | None:
    """Return authenticated user if a valid Bearer token is present, else None."""
    auth_header = request.headers.get("Authorization") or ""
    if not auth_header.strip():
        return None
    return get_user_from_token(auth_header)


def get_required_auth_user(request: Request) -> dict[str, Any]:
    """Require a valid Bearer token or raise ValueError."""
    auth_header = request.headers.get("Authorization") or ""
    user = get_user_from_token(auth_header)
    if not user:
        raise ValueError("Unauthorized: missing or invalid authorization token.")
    return user


def resolve_farm(request: Request, payload: dict[str, Any]) -> Farm:
    """Resolve a Farm either from a saved farm_id (when authenticated) or inline JSON."""
    farm_id = payload.get("farm_id")
    if farm_id is not None and not payload.get("farm"):
        user = get_optional_auth_user(request)
        if not user:
            raise ValueError("Authentication required to load a saved farm by farm_id.")
        saved = next((f for f in list_user_farms(user["id"]) if f["id"] == int(farm_id)), None)
        if not saved:
            raise ValueError(f"Saved farm #{farm_id} not found for current user.")
        merged = dict(saved.get("farm") or {})
        if payload.get("windows"):
            merged["windows"] = payload["windows"]
        return parse_farm(merged)
    return parse_farm(payload)
