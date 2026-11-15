"""Agricultural context builder for Cresco AI with strict provenance labeling."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date
import re
from typing import Any, Callable

from agroshift.decision import Farm, Window
from agroshift.earth_data.autofill import derive_field_autofill
from agroshift.earth_data.geometry import normalize_boundary, polygon_centroid
from agroshift.identity import list_user_farms
from agroshift.monitoring.engine_3d import build_3d_field_slab
from agroshift.monitoring.live_monitor import evaluate_live_rotation_state
from agroshift.rotation import RotationConfig, plan_global_rotations
from agroshift.science.climate.climate_insights import seasonal_weather_risk_summary
from agroshift.science.decision.screening import find_options
from agroshift.science.knowledge.knowledge import (
    global_traits,
    pest_context,
    search_crops,
)
from agroshift.science.soil_water.water_balance import seasonal_water_balance_summary


PROVENANCE_VALUES = (
    "measured",
    "observed",
    "modeled",
    "estimated",
    "reviewed",
    "unavailable",
)


def _val_or_unavailable(value: Any, provenance: str) -> dict[str, Any]:
    """Wrap a scalar or structured value with its provenance; never coerce None to 0."""
    if value is None or value == "" or value == "unknown":
        return {"value": None, "provenance": "unavailable"}
    return {"value": value, "provenance": provenance}


def _parse_windows_from_dict(raw: dict[str, Any]) -> tuple[Window, ...]:
    raw_windows = raw.get("windows")
    if isinstance(raw_windows, (list, tuple)) and raw_windows:
        parsed: list[Window] = []
        for item in raw_windows:
            if isinstance(item, Window):
                parsed.append(item)
            elif isinstance(item, dict) and "start_month" in item and "end_month" in item:
                parsed.append(
                    Window(
                        int(item["start_month"]),
                        int(item.get("start_day", 1)),
                        int(item["end_month"]),
                        int(item.get("end_day", 28)),
                    )
                )
        if parsed:
            return tuple(parsed)
    sowing_raw = raw.get("sowing_date") or raw.get("start_date")
    if sowing_raw:
        try:
            dt = date.fromisoformat(str(sowing_raw).strip()[:10])
            end_month = ((dt.month - 1 + 3) % 12) + 1
            return (Window(dt.month, dt.day, end_month, min(dt.day, 28)),)
        except Exception:
            pass
    return (Window(5, 1, 8, 31),)


def _build_farm_object(raw: dict[str, Any]) -> Farm:
    defaults = Farm()
    ph = raw.get("ph")
    area_ha = raw.get("area_ha", raw.get("areaHectares"))
    irrigation_mm = raw.get("irrigation_mm")
    rain_fraction = raw.get("rain_fraction")
    current_crop = raw.get("current") or raw.get("crop_id") or "unknown"
    return Farm(
        latitude=float(raw["latitude"]),
        longitude=float(raw["longitude"]),
        country=str(raw.get("country") or defaults.country).upper(),
        area_ha=float(area_ha) if area_ha is not None else None,
        previous=str(raw.get("previous") or "unknown"),
        current=str(current_crop),
        baseline=tuple(raw.get("baseline") or defaults.baseline),
        allowed=tuple(raw.get("allowed") or defaults.allowed),
        drainage=str(raw.get("drainage") or "unknown"),
        ph=float(ph) if ph is not None else None,
        irrigation=str(raw.get("irrigation") or "unknown"),
        irrigation_mm=float(irrigation_mm) if irrigation_mm is not None else None,
        rain_fraction=float(rain_fraction) if rain_fraction is not None else None,
        windows=_parse_windows_from_dict(raw),
        pilot_confirmed=bool(raw.get("pilot_confirmed", False)),
        season_name=str(raw.get("season_name") or raw.get("season") or "Selected season"),
    )


def _resolve_raw_farm(
    *,
    user_id: int | None,
    farm_id: str | int | None,
    inline_farm: dict[str, Any] | None,
    season: str | None,
    area_id: str | None,
) -> dict[str, Any]:
    saved_record: dict[str, Any] | None = None
    if farm_id is not None and user_id is not None:
        try:
            fid_int = int(farm_id)
            farms = list_user_farms(user_id)
            saved_record = next((f for f in farms if f["id"] == fid_int), None)
        except (TypeError, ValueError):
            saved_record = None

    merged: dict[str, Any] = {}
    if saved_record:
        merged.update(saved_record.get("farm") or {})
        merged["farm_id"] = saved_record.get("id")
        merged["name"] = saved_record.get("name")
        merged["country"] = saved_record.get("country", merged.get("country"))
        merged["latitude"] = saved_record.get("latitude", merged.get("latitude"))
        merged["longitude"] = saved_record.get("longitude", merged.get("longitude"))
        merged["area_ha"] = saved_record.get("area_ha", merged.get("area_ha"))
        if saved_record.get("boundary") and not merged.get("boundary"):
            merged["boundary"] = saved_record.get("boundary")

    if isinstance(inline_farm, dict):
        for key, value in inline_farm.items():
            if value is not None:
                merged[key] = value

    if farm_id is not None and "farm_id" not in merged:
        merged["farm_id"] = farm_id
    if season:
        merged["season_name"] = season
    if area_id:
        merged["area_id"] = area_id

    if (merged.get("latitude") is None or merged.get("longitude") is None) and merged.get("boundary"):
        poly = normalize_boundary(merged.get("boundary"))
        centroid = polygon_centroid(poly)
        if centroid:
            merged["latitude"], merged["longitude"] = centroid

    return merged


def _select_relevant_crops(
    *,
    user_message: str,
    farm: Farm | None,
    screened_cards: list[dict[str, Any]],
    max_crops: int = 12,
) -> dict[str, Any]:
    """Select only crops relevant to the user's question and farm, never all 107+."""
    all_crops = search_crops(limit=250)
    by_id = {c["id"]: c for c in all_crops}
    msg_lower = (user_message or "").lower()
    tokens = set(re.findall(r"[a-z0-9_]+", msg_lower))

    selected_ids: list[str] = []

    def _add(cid: str | None) -> None:
        if cid and cid in by_id and cid not in selected_ids:
            selected_ids.append(cid)

    # 1. Explicitly mentioned crops in user message
    for cid, c in by_id.items():
        name_l = str(c.get("name") or "").lower()
        cid_space = cid.replace("_", " ")
        if cid in tokens or cid_space in msg_lower or (name_l and name_l in msg_lower):
            _add(cid)

    # 2. Current & previous farm crops
    if farm is not None:
        if farm.current not in ("unknown", "none", ""):
            _add(farm.current)
        if farm.previous not in ("unknown", "none", ""):
            _add(farm.previous)

    # 3. Top screened candidates (possible first, then check)
    card_by_id = {c["id"]: c for c in screened_cards if isinstance(c, dict) and c.get("id")}
    for status_target in ("possible", "check"):
        for card in screened_cards:
            if len(selected_ids) >= max_crops:
                break
            if card.get("status") == status_target:
                _add(card.get("id"))

    selected_ids = selected_ids[:max_crops]

    traits_by_crop: dict[str, dict[str, Any]] = defaultdict(dict)
    for t in global_traits():
        cid = t.get("crop_id")
        if cid in selected_ids and t.get("review_status") == "reviewed":
            traits_by_crop[cid][t["trait"]] = {
                "low": t.get("low"),
                "high": t.get("high"),
                "value": t.get("value"),
                "unit": t.get("unit"),
            }

    pests_by_crop: dict[str, list[str]] = defaultdict(list)
    for p in pest_context():
        cid = p.get("crop_id")
        if cid in selected_ids and len(pests_by_crop[cid]) < 4:
            pests_by_crop[cid].append(
                f"{p.get('category', 'pest')}: {p.get('agent_name', 'unknown')}"
            )

    items: list[dict[str, Any]] = []
    for cid in selected_ids:
        c = by_id[cid]
        card = card_by_id.get(cid)
        items.append(
            {
                "id": cid,
                "name": c.get("name"),
                "family": c.get("family"),
                "screening_status": card.get("status") if card else None,
                "screening_summary": card.get("summary") if card else None,
                "traits": traits_by_crop.get(cid, {}),
                "key_pests": pests_by_crop.get(cid, []),
                "provenance": "reviewed",
            }
        )

    counts = None
    if screened_cards:
        counts = {
            "total_catalog": len(all_crops),
            "screened": len(screened_cards),
            "possible": sum(1 for c in screened_cards if c.get("status") == "possible"),
            "check": sum(1 for c in screened_cards if c.get("status") == "check"),
            "outside": sum(1 for c in screened_cards if c.get("status") == "outside"),
            "blocked": sum(1 for c in screened_cards if c.get("status") == "blocked"),
        }

    return {
        "selection_counts": counts or {"total_catalog": len(all_crops), "returned": len(items)},
        "relevant_crops": items,
        "provenance": "reviewed",
    }


def _extract_nasa_climate_summary(ds: Any, farm: Farm) -> dict[str, Any]:
    if ds is None or not hasattr(ds, "frame") or ds.frame.empty:
        return {"provenance": "unavailable", "note": "Climate dataset unavailable."}

    frame = ds.frame
    prov_text = str(getattr(ds, "provenance", "") or "")
    is_nasa = "nasa" in prov_text.lower() or "power" in prov_text.lower()
    prov_label = "observed" if is_nasa else "modeled"

    dates_min = str(frame.index.min())[:10] if len(frame.index) else None
    dates_max = str(frame.index.max())[:10] if len(frame.index) else None

    risk = None
    water_bal = None
    try:
        risk = seasonal_weather_risk_summary(ds, farm.windows[0])
    except Exception:
        risk = None
    try:
        water_bal = seasonal_water_balance_summary(ds, farm)
    except Exception:
        water_bal = None

    return {
        "provenance": prov_label,
        "source": prov_text if is_nasa else (prov_text or "AgroShift climate archive"),
        "is_nasa_power": is_nasa,
        "date_range": {"start": dates_min, "end": dates_max},
        "seasonal_weather_risk": risk,
        "seasonal_water_balance": water_bal,
    }


def build_agricultural_context(
    *,
    user_id: int | None,
    farm_id: str | int | None = None,
    inline_farm: dict[str, Any] | None = None,
    season: str | None = None,
    area_id: str | None = None,
    user_message: str = "",
    dataset_loader: Callable[[float, float], Any] | None = None,
) -> dict[str, Any]:
    """Build grounded farm, soil/3D, climate, water, crop, and rotation context."""
    raw_farm = _resolve_raw_farm(
        user_id=user_id,
        farm_id=farm_id,
        inline_farm=inline_farm,
        season=season,
        area_id=area_id,
    )

    has_coords = raw_farm.get("latitude") is not None and raw_farm.get("longitude") is not None
    farm_obj: Farm | None = None
    ds: Any = None
    autofill_data: dict[str, Any] | None = None
    slab_data: dict[str, Any] | None = None
    screened_cards: list[dict[str, Any]] = []
    rotations_summary: dict[str, Any] = {"provenance": "unavailable", "plans": []}

    if has_coords:
        farm_obj = _build_farm_object(raw_farm)
        if dataset_loader is not None:
            try:
                ds = dataset_loader(farm_obj.latitude, farm_obj.longitude)
            except Exception:
                ds = None

        try:
            autofill_data = derive_field_autofill(
                farm_obj.latitude,
                farm_obj.longitude,
                farm_obj.country,
                boundary=raw_farm.get("boundary"),
                area_ha=farm_obj.area_ha,
                dataset=ds,
                offline=True,
            ).get("autofill")
        except Exception:
            autofill_data = None

        try:
            slab_data = build_3d_field_slab(
                farm_obj.latitude,
                farm_obj.longitude,
                farm_obj.country,
                boundary=raw_farm.get("boundary"),
                area_ha=farm_obj.area_ha,
                dataset=ds,
                offline=True,
                stage="fast",
                precomputed_autofill=autofill_data,
            )
        except Exception:
            slab_data = None

        if ds is not None:
            try:
                screened_cards = find_options(farm_obj, ds)
            except Exception:
                screened_cards = []

            try:
                plans = plan_global_rotations(
                    farm_obj,
                    ds,
                    config=RotationConfig(max_sequences=3),
                )
                top_plans = plans[:3]
                live_eval = None
                if top_plans and farm_obj.current not in ("unknown", "none", ""):
                    try:
                        live_eval = evaluate_live_rotation_state(top_plans)
                    except Exception:
                        live_eval = None
                rotations_summary = {
                    "provenance": "modeled",
                    "plans": [
                        {
                            "rank": p.get("rank"),
                            "ease_rank": p.get("ease_rank"),
                            "name": p.get("name"),
                            "overall_status": p.get("overall_status"),
                            "rating": p.get("rating"),
                            "score": p.get("score"),
                            "season_1": (p.get("season_1") or {}).get("crop_name") or (p.get("season_1") or {}).get("crop_id"),
                            "season_2": (p.get("season_2") or {}).get("crop_name") or (p.get("season_2") or {}).get("crop_id"),
                            "summary": p.get("summary"),
                        }
                        for p in top_plans
                    ],
                    "live_monitor": live_eval.get("plain_rotations", [])[:2]
                    if isinstance(live_eval, dict)
                    else None,
                }
            except Exception:
                rotations_summary = {"provenance": "unavailable", "plans": []}

    # Farm profile with explicit provenance
    af_ph = ((autofill_data or {}).get("ph") or {}).get("value")
    af_drainage = ((autofill_data or {}).get("drainage") or {}).get("value")
    ph_measured = raw_farm.get("ph") is not None
    drainage_measured = raw_farm.get("drainage") not in (None, "", "unknown")

    soil_block: dict[str, Any] = {
        "ph": (
            _val_or_unavailable(raw_farm.get("ph"), "measured")
            if ph_measured
            else _val_or_unavailable(af_ph, "modeled")
        ),
        "drainage": (
            _val_or_unavailable(raw_farm.get("drainage"), "measured")
            if drainage_measured
            else _val_or_unavailable(af_drainage, "modeled")
        ),
        "slab_3d": {"provenance": "unavailable"},
    }
    if isinstance(slab_data, dict):
        soil_block["slab_3d"] = {
            "provenance": "modeled",
            "fusion_stage": slab_data.get("fusion_stage"),
            "soil_horizons": slab_data.get("soil_3d_horizons", {}).get("horizons")
            if isinstance(slab_data.get("soil_3d_horizons"), dict)
            else None,
            "terrain_summary": {
                k: v
                for k, v in (slab_data.get("terrain_3d_mesh") or {}).items()
                if k in ("elevation_m", "regional_slope_pct", "suggested_drainage_prior")
            }
            if isinstance(slab_data.get("terrain_3d_mesh"), dict)
            else None,
        }

    # Satellite overpass dates (only observed if real acquisitions exist)
    sat_block: dict[str, Any] = {"provenance": "unavailable", "acquisitions": []}
    if isinstance(slab_data, dict):
        overpasses = slab_data.get("overpass_schedule") or slab_data.get("satellite") or {}
        acqs = overpasses.get("acquisitions") if isinstance(overpasses, dict) else None
        if acqs:
            sat_block = {
                "provenance": "observed",
                "source": overpasses.get("source") or "Satellite overpass schedule",
                "acquisitions": acqs[:5],
            }

    climate_block = (
        _extract_nasa_climate_summary(ds, farm_obj)
        if farm_obj is not None
        else {"provenance": "unavailable"}
    )

    water_block = {
        "irrigation_type": _val_or_unavailable(
            raw_farm.get("irrigation"), "measured" if raw_farm.get("irrigation") not in (None, "", "unknown") else "unavailable"
        ),
        "irrigation_mm": _val_or_unavailable(raw_farm.get("irrigation_mm"), "measured"),
        "rain_fraction": _val_or_unavailable(raw_farm.get("rain_fraction"), "measured"),
    }

    farm_profile = {
        "farm_id": raw_farm.get("farm_id"),
        "name": raw_farm.get("name"),
        "area_id": area_id,
        "season": raw_farm.get("season_name") or season,
        "country": raw_farm.get("country"),
        "latitude": _val_or_unavailable(raw_farm.get("latitude"), "measured"),
        "longitude": _val_or_unavailable(raw_farm.get("longitude"), "measured"),
        "area_ha": _val_or_unavailable(raw_farm.get("area_ha"), "measured"),
        "current_crop": _val_or_unavailable(
            raw_farm.get("current") or raw_farm.get("crop_id"), "measured"
        ),
        "previous_crop": _val_or_unavailable(raw_farm.get("previous"), "measured"),
        "windows": [asdict(w) for w in farm_obj.windows] if farm_obj else [],
    }

    crop_knowledge = _select_relevant_crops(
        user_message=user_message,
        farm=farm_obj,
        screened_cards=screened_cards,
    )

    provenance_summary = {
        "climate": climate_block.get("provenance", "unavailable"),
        "soil_ph": soil_block["ph"]["provenance"],
        "drainage": soil_block["drainage"]["provenance"],
        "soil_3d": soil_block["slab_3d"]["provenance"],
        "satellite": sat_block["provenance"],
        "crops": crop_knowledge.get("provenance", "reviewed"),
        "rotation": rotations_summary.get("provenance", "unavailable"),
    }

    return {
        "farm_context": {
            "profile": farm_profile,
            "soil": soil_block,
            "climate": climate_block,
            "water": water_block,
            "satellite": sat_block,
        },
        "crop_knowledge_context": crop_knowledge,
        "rotation_context": rotations_summary,
        "provenance_summary": provenance_summary,
    }
