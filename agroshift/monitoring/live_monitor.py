"""Live t > 0 rotation uncertainty, satellite canopy assimilation, and expiry monitor."""
from __future__ import annotations

from datetime import date, timedelta
import math
from typing import Any

from agroshift.science.knowledge.knowledge import global_traits


def _expected_ndvi_at_progress(progress_frac: float) -> float:
    """FAO-56 style canopy NDVI proxy curve over normalized cycle progress [0.0, 1.0]."""
    f = max(0.0, min(1.0, float(progress_frac)))
    if f < 0.18:
        return round(0.18 + (f / 0.18) * 0.12, 3)
    if f < 0.46:
        return round(0.30 + ((f - 0.18) / 0.28) * 0.52, 3)
    if f < 0.80:
        return 0.82
    return round(0.82 - ((f - 0.80) / 0.20) * 0.47, 3)


def _max_rooting_depth_for_crop(crop_id: str, traits_index: dict[str, float]) -> float:
    """Lookup reviewed max_rooting_depth_m midpoint for a crop, defaulting to 1.0 m."""
    return traits_index.get(crop_id, 1.0)


def _build_rooting_depth_index() -> dict[str, float]:
    """Build crop_id -> max_rooting_depth_m index from reviewed global traits."""
    index: dict[str, float] = {}
    try:
        for t in global_traits():
            if (
                t.get("trait") == "max_rooting_depth_m"
                and t.get("review_status") == "reviewed"
                and t.get("scope") == "global"
            ):
                cid = str(t.get("crop_id", ""))
                if "value" in t and t["value"] is not None:
                    index[cid] = float(t["value"])
                elif "low" in t and "high" in t:
                    index[cid] = 0.5 * (float(t["low"]) + float(t["high"]))
    except Exception:
        pass
    return index


def _sigma_days(t_day: int, t_now_day: int, weather_volatility: float) -> float:
    """Expanding future uncertainty standard deviation in days for t > t_now_day."""
    if t_day <= t_now_day:
        return 0.0
    return round(1.5 + weather_volatility * math.sqrt(max(0, t_day - t_now_day)) * 4.0, 1)


def _determine_active_stage(effective_day: int, stages: list[dict[str, Any]], d_nom: int) -> str:
    """Map effective biological day onto FAO growth stage key."""
    if not stages:
        frac = effective_day / max(1, d_nom)
        if frac < 0.18:
            return "initial_emergence"
        if frac < 0.46:
            return "canopy_development"
        if frac < 0.80:
            return "mid_season_flowering_peak_water"
        return "late_season_ripening"

    elapsed = 0
    for st in stages:
        dur = max(1, int(st.get("duration_days", 1)))
        elapsed += dur
        if effective_day <= elapsed:
            return str(st.get("stage", "unknown"))
    return str(stages[-1].get("stage", "late_season_ripening"))


def evaluate_live_rotation_state(
    rotations: list[dict[str, Any]],
    *,
    t_now_day: int = 42,
    observed_ndvi: float | None = None,
    weather_volatility: float = 0.18,
) -> dict[str, Any]:
    """Evaluate live t > 0 rotation state, collapsing past uncertainty and projecting future cone.

    Returns both ``plain_rotations`` (sorted by ``rank``) and ``easiness_rotations``
    (sorted by ``ease_rank``) side-by-side.
    """
    t_now = max(0, int(t_now_day))
    vol = max(0.0, float(weather_volatility))
    root_index = _build_rooting_depth_index()

    evaluated: list[dict[str, Any]] = []
    for rot in rotations:
        item = dict(rot)
        timeline = rot.get("timeline") or {}
        slots = timeline.get("slots") or []

        if not slots:
            item["live_state"] = {
                "t_now_day": t_now,
                "growth_lag_days": 0,
                "active_stage": "unknown",
                "active_root_depth_m": 0.15,
                "expected_ndvi": None,
                "observed_ndvi": observed_ndvi,
                "safe_expiry_date": timeline.get("safe_expiry_date"),
                "hard_expiry_date": timeline.get("hard_expiry_date"),
                "days_until_safe_expiry": timeline.get("days_until_safe_expiry", 0),
                "days_until_hard_expiry": timeline.get("days_until_hard_expiry", 0),
                "sigma_at_harvest_days": 0.0,
                "uncertainty_cone_series": [],
            }
            evaluated.append(item)
            continue

        slot1 = slots[0]
        sow_date = date.fromisoformat(slot1["sowing_date"])
        cycle = slot1.get("growth_cycle_days") or {}
        d_nom = max(1, int(cycle.get("nominal", 115)))
        stages = slot1.get("stages") or []

        raw_frac = min(1.0, t_now / d_nom)
        expected_ndvi = _expected_ndvi_at_progress(raw_frac)

        if observed_ndvi is not None:
            ndvi_delta = float(observed_ndvi) - expected_ndvi
            if raw_frac < 0.80:
                growth_lag_days = int(round(-ndvi_delta * d_nom * 0.35))
            else:
                growth_lag_days = int(round(ndvi_delta * d_nom * 0.25))
            growth_lag_days = max(-21, min(28, growth_lag_days))
        else:
            growth_lag_days = 0

        effective_day = max(0, t_now - growth_lag_days)
        effective_frac = min(1.0, effective_day / d_nom)

        buf_days = int(slot1.get("turnaround_buffer_after_days", 0))
        if t_now > d_nom + growth_lag_days and len(slots) > 1:
            if t_now < d_nom + growth_lag_days + max(0, buf_days):
                active_stage = "turnaround_prep"
                active_crop_id = str(slot1.get("crop_id", ""))
                active_frac = 1.0
            else:
                slot2 = slots[1]
                d2_nom = max(1, int((slot2.get("growth_cycle_days") or {}).get("nominal", 100)))
                s2_day = max(0, t_now - (d_nom + growth_lag_days + max(0, buf_days)))
                active_stage = _determine_active_stage(s2_day, slot2.get("stages") or [], d2_nom)
                active_crop_id = str(slot2.get("crop_id", ""))
                active_frac = min(1.0, s2_day / d2_nom)
        else:
            active_stage = _determine_active_stage(effective_day, stages, d_nom)
            active_crop_id = str(slot1.get("crop_id", ""))
            active_frac = effective_frac

        max_root = _max_rooting_depth_for_crop(active_crop_id, root_index)
        if active_frac <= 0.0:
            active_root_depth_m = 0.15
        elif active_frac >= 0.46:
            active_root_depth_m = round(max_root, 2)
        else:
            active_root_depth_m = round(0.15 + (active_frac / 0.46) * max(0.0, max_root - 0.15), 2)

        # Build time-series uncertainty cone across Slot 1 cycle (0 .. d_nom)
        sample_days = sorted(
            {0, t_now, d_nom}
            | set(range(0, d_nom + 1, 7))
        )
        cone_series: list[dict[str, Any]] = []
        for day in sample_days:
            if day > max(d_nom, t_now):
                continue
            is_past = day <= t_now
            nom_day = max(0, day - growth_lag_days)
            nom_pct = round(max(0.0, min(100.0, (nom_day / d_nom) * 100.0)), 1)
            if is_past:
                opt_pct = nom_pct
                pess_pct = nom_pct
            else:
                sig = _sigma_days(day, t_now, vol)
                opt_pct = round(max(0.0, min(100.0, ((nom_day + sig) / d_nom) * 100.0)), 1)
                pess_pct = round(max(0.0, min(100.0, ((nom_day - sig) / d_nom) * 100.0)), 1)

            cone_series.append(
                {
                    "day": day,
                    "nominal_progress_pct": nom_pct,
                    "optimistic_bound_pct": opt_pct,
                    "pessimistic_bound_pct": pess_pct,
                    "is_observed_past": is_past,
                }
            )

        # Live shifted expiry dates
        current_date = sow_date + timedelta(days=t_now)
        base_safe_str = timeline.get("safe_expiry_date") or slot1.get("safe_expiry_date")
        base_hard_str = timeline.get("hard_expiry_date") or slot1.get("hard_expiry_date")
        sigma_harvest = _sigma_days(d_nom, t_now, vol)

        if base_safe_str:
            live_safe_date = date.fromisoformat(base_safe_str) - timedelta(days=growth_lag_days)
            live_safe_iso = live_safe_date.isoformat()
            live_days_safe = (live_safe_date - current_date).days
        else:
            live_safe_iso = None
            live_days_safe = 0

        if base_hard_str:
            live_hard_date = date.fromisoformat(base_hard_str) - timedelta(days=growth_lag_days)
            live_hard_iso = live_hard_date.isoformat()
            live_days_hard = (live_hard_date - current_date).days
        else:
            live_hard_iso = None
            live_days_hard = 0

        item["live_state"] = {
            "t_now_day": t_now,
            "current_date": current_date.isoformat(),
            "growth_lag_days": growth_lag_days,
            "active_stage": active_stage,
            "active_root_depth_m": active_root_depth_m,
            "expected_ndvi": expected_ndvi,
            "observed_ndvi": observed_ndvi,
            "safe_expiry_date": live_safe_iso,
            "hard_expiry_date": live_hard_iso,
            "days_until_safe_expiry": live_days_safe,
            "days_until_hard_expiry": live_days_hard,
            "sigma_at_harvest_days": sigma_harvest,
            "uncertainty_cone_series": cone_series,
        }
        evaluated.append(item)

    plain_rotations = sorted(evaluated, key=lambda r: r.get("rank", 9999))
    easiness_rotations = sorted(evaluated, key=lambda r: r.get("ease_rank", 9999))

    return {
        "t_now_day": t_now,
        "observed_ndvi": observed_ndvi,
        "weather_volatility": vol,
        "plain_rotations": plain_rotations,
        "easiness_rotations": easiness_rotations,
    }
