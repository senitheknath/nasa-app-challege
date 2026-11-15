"""Agro-ecological quantizer and physical timeline adapter.

Translates real-world NASA POWER weather windows, SoilGrids observations, and
reviewed FAO crop coefficients into the pure mathematical scheduling core
(ActivityNode, ArcConstraint), then translates solved trajectories back into
physical calendar milestones, stage dates, turnaround buffers, and delay slack.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Sequence

from .contracts import CropProfile, EnvironmentContext, RotationConfig
from .timeline_core import (
    ActivityNode,
    ArcConstraint,
    ScheduledSlot,
    Trajectory,
    solve_trajectories,
)


def _cycle_bounds_from_profile(profile: CropProfile) -> tuple[int, int, int]:
    """Extract (min, nominal, max) cycle duration in days from crop profile traits."""
    dur_trait = profile.trait_value("indicative_cycle_duration")
    if isinstance(dur_trait, tuple) and len(dur_trait) == 2:
        d_min = int(round(float(dur_trait[0])))
        d_max = int(round(float(dur_trait[1])))
        d_nom = int(round(0.5 * (d_min + d_max)))
        return (max(45, d_min), max(d_min, d_nom), max(d_nom, d_max))
    elif isinstance(dur_trait, (int, float)):
        d = int(round(float(dur_trait)))
        return (max(45, int(d * 0.9)), d, int(d * 1.15))

    # Standard agronomic defaults based on group
    if profile.life_cycle == "perennial":
        return (365, 365, 730)
    if profile.is_nitrogen_fixer:
        return (75, 95, 115)
    return (90, 115, 140)


def _fao_stage_fractions_from_profile(profile: CropProfile) -> tuple[float, ...]:
    """Extract standard 4-stage fractions (initial, dev, mid, late) from profile."""
    # FAO-56 typical fraction partition
    return (0.18, 0.28, 0.34, 0.20)


_STAGE_LABELS = [
    ("initial_emergence", "Emergence & Root Establishment"),
    ("canopy_development", "Rapid Vegetative Canopy Growth"),
    ("mid_season_flowering_peak_water", "Flowering & Peak Water Demand (Kc max)"),
    ("late_season_ripening", "Grain Fill & Ripening"),
]

_UTILITY_MAP = {
    "possible": 15.0,
    "check": 8.0,
    "conditional": 5.0,
    "outside": -10.0,
    "blocked": -50.0,
}


def _latest_start_offset(start_offset: int, window_len: int, d_min: int) -> int:
    """Compute latest feasible start offset within a seasonal window."""
    if window_len > d_min:
        return start_offset + max(14, min(window_len - d_min, int(window_len * 0.45)))
    return start_offset + 14


def _phase_intervals(start_t: int, duration: int, fractions: tuple[float, ...]) -> list[tuple[int, int]]:
    """Partition activity duration into discrete phase intervals [p_start, p_end]."""
    intervals: list[tuple[int, int]] = []
    curr = start_t
    n_phases = len(fractions)
    for i, frac in enumerate(fractions):
        if i == n_phases - 1:
            p_end = start_t + duration
        else:
            p_len = max(1, int(round(duration * frac)))
            p_end = min(start_t + duration, curr + p_len)
        intervals.append((curr, p_end))
        curr = p_end
    return intervals


def _turnaround_summary(buffer_days: int) -> dict[str, Any]:
    """Classify turnaround gap between consecutive slots."""
    if buffer_days < 0:
        buf_status = "collision"
        buf_desc = f"Season 1 harvest collides with Season 2 planting by {abs(buffer_days)} days."
    elif buffer_days < 7:
        buf_status = "tight"
        buf_desc = f"{buffer_days}-day turnaround is tight; high risk if late rains delay harvest."
    elif buffer_days <= 35:
        buf_status = "optimal"
        buf_desc = f"{buffer_days}-day turnaround allows ideal field drying, plowing, and seedbed prep."
    else:
        buf_status = "excessive_fallow"
        buf_desc = f"{buffer_days}-day gap leaves soil bare; consider a short cover crop to prevent erosion."
    return {
        "buffer_days": buffer_days,
        "status": buf_status,
        "advisory": buf_desc,
    }


def quantize_crop_to_activity(
    profile: CropProfile,
    window: Any,
    card: dict[str, Any],
    *,
    ref_year: int = 2024,
) -> ActivityNode:
    """Convert a biological CropProfile and seasonal Window into a mathematical ActivityNode."""
    s_date, e_date = window.dates(ref_year)
    base_jan1 = date(ref_year, 1, 1)

    start_offset = (s_date - base_jan1).days
    window_len = (e_date - s_date).days
    d_min, d_nom, d_max = _cycle_bounds_from_profile(profile)
    latest_start = _latest_start_offset(start_offset, window_len, d_min)
    phase_fracs = _fao_stage_fractions_from_profile(profile)

    status = card.get("status", "unknown")
    base_util = _UTILITY_MAP.get(status, 0.0)

    return ActivityNode(
        id=profile.id,
        earliest_start=start_offset,
        latest_start=latest_start,
        duration_min=d_min,
        duration_nominal=d_nom,
        duration_max=d_max,
        phase_fractions=phase_fracs,
        base_utility=base_util,
        payload={
            "crop_id": profile.id,
            "crop_name": profile.name,
            "family": profile.family,
            "profile": profile,
            "window_label": getattr(window, "label", ""),
            "s_date": s_date,
            "e_date": e_date,
            "card": card,
        },
    )


def build_physical_timeline(
    trajectory: Trajectory,
    *,
    ref_year: int = 2024,
) -> dict[str, Any]:
    """Translate a mathematical Trajectory into physical calendar milestones and delay buffers."""
    base_jan1 = date(ref_year, 1, 1)
    slots_output: list[dict[str, Any]] = []
    traj_slots = trajectory.slots

    for idx, slot in enumerate(traj_slots):
        p = slot.payload
        profile: CropProfile = p["profile"]

        sow_date = base_jan1 + timedelta(days=slot.start_t)
        harvest_nominal = base_jan1 + timedelta(days=slot.end_t_nominal)
        harvest_early = base_jan1 + timedelta(days=slot.end_t_min)
        harvest_late = base_jan1 + timedelta(days=slot.end_t_max)

        d_nom = slot.end_t_nominal - slot.start_t
        d_max = slot.end_t_max - slot.start_t

        if idx + 1 < len(traj_slots):
            nxt_slot = traj_slots[idx + 1]
            nxt_latest = (
                nxt_slot.latest_start
                if nxt_slot.latest_start is not None
                else nxt_slot.start_t + nxt_slot.delay_slack
            )
            min_buf = slot.min_buffer_after
            safe_expiry_t = nxt_latest - min_buf - d_max
            hard_expiry_t = nxt_latest - min_buf - d_nom
            deadline_t = nxt_latest - min_buf
            if slot.end_t_max <= deadline_t:
                collision_prob = 0.0
            elif slot.end_t_min > deadline_t:
                collision_prob = 100.0
            else:
                span = max(1, slot.end_t_max - slot.end_t_min)
                collision_prob = round(max(0.0, min(100.0, ((slot.end_t_max - deadline_t) / span) * 100.0)), 1)
        else:
            own_latest = slot.latest_start if slot.latest_start is not None else slot.start_t + slot.delay_slack
            hard_expiry_t = own_latest
            safe_expiry_t = own_latest - max(0, d_max - d_nom)
            collision_prob = 0.0

        safe_expiry_date = (base_jan1 + timedelta(days=safe_expiry_t)).isoformat()
        hard_expiry_date = (base_jan1 + timedelta(days=hard_expiry_t)).isoformat()
        days_until_safe_expiry = safe_expiry_t - slot.start_t
        days_until_hard_expiry = hard_expiry_t - slot.start_t

        stages = _build_stages_output(base_jan1, slot.phase_intervals)

        slots_output.append(
            {
                "crop_id": profile.id,
                "crop_name": profile.name,
                "family": profile.family,
                "window": p.get("window_label", ""),
                "sowing_date": sow_date.isoformat(),
                "harvest_nominal_date": harvest_nominal.isoformat(),
                "harvest_window": {
                    "early_maturity": harvest_early.isoformat(),
                    "nominal_maturity": harvest_nominal.isoformat(),
                    "late_maturity": harvest_late.isoformat(),
                },
                "growth_cycle_days": {
                    "minimum": slot.end_t_min - slot.start_t,
                    "nominal": d_nom,
                    "maximum": d_max,
                },
                "stages": stages,
                "kc_max": profile.kc_max,
                "delay_slack_days": slot.delay_slack,
                "turnaround_buffer_after_days": slot.turnaround_buffer_after,
                "safe_expiry_date": safe_expiry_date,
                "hard_expiry_date": hard_expiry_date,
                "days_until_safe_expiry": days_until_safe_expiry,
                "days_until_hard_expiry": days_until_hard_expiry,
                "collision_probability_pct": collision_prob,
                "uncertainty_cone": {
                    "early_end_date": harvest_early.isoformat(),
                    "nominal_end_date": harvest_nominal.isoformat(),
                    "late_end_date": harvest_late.isoformat(),
                    "span_days": slot.end_t_max - slot.end_t_min,
                },
            }
        )

    # Evaluate turnaround buffer between Season 1 and Season 2
    buffer_days = slots_output[0]["turnaround_buffer_after_days"] if len(slots_output) > 1 else 0

    first_slot = slots_output[0] if slots_output else {}
    return {
        "overall_status": trajectory.status,
        "feasible": trajectory.feasible,
        "total_agronomic_score": trajectory.total_score,
        "safe_expiry_date": first_slot.get("safe_expiry_date"),
        "hard_expiry_date": first_slot.get("hard_expiry_date"),
        "days_until_safe_expiry": first_slot.get("days_until_safe_expiry", 0),
        "days_until_hard_expiry": first_slot.get("days_until_hard_expiry", 0),
        "collision_probability_pct": first_slot.get("collision_probability_pct", 0.0),
        "uncertainty_cone": {
            "slot_1_span_days": first_slot.get("uncertainty_cone", {}).get("span_days", 0),
            "slot_2_span_days": slots_output[1].get("uncertainty_cone", {}).get("span_days", 0) if len(slots_output) > 1 else 0,
            "collision_probability_pct": first_slot.get("collision_probability_pct", 0.0),
        },
        "turnaround_summary": _turnaround_summary(buffer_days),
        "slots": slots_output,
    }


def _build_stages_output(
    base_jan1: date,
    phase_intervals: list[tuple[int, int]],
) -> list[dict[str, Any]]:
    """Build FAO-56 stage milestone dictionaries from discrete day intervals."""
    stages: list[dict[str, Any]] = []
    for (stage_key, stage_desc), (p_s, p_e) in zip(_STAGE_LABELS, phase_intervals):
        stages.append(
            {
                "stage": stage_key,
                "description": stage_desc,
                "start_date": (base_jan1 + timedelta(days=p_s)).isoformat(),
                "end_date": (base_jan1 + timedelta(days=p_e)).isoformat(),
                "duration_days": p_e - p_s,
            }
        )
    return stages


def _build_slot_dict(
    *,
    profile: CropProfile,
    window_label: str,
    base_jan1: date,
    start_t: int,
    d_min: int,
    d_nom: int,
    d_max: int,
    phase_fracs: tuple[float, ...],
    delay_slack: int,
    turnaround_buffer_after: int,
    safe_expiry_t: int,
    hard_expiry_t: int,
    collision_prob: float,
) -> dict[str, Any]:
    """Assemble a single slot dictionary matching build_physical_timeline() output."""
    end_min = start_t + d_min
    end_nom = start_t + d_nom
    end_max = start_t + d_max

    sow_date = base_jan1 + timedelta(days=start_t)
    harvest_early = base_jan1 + timedelta(days=end_min)
    harvest_nominal = base_jan1 + timedelta(days=end_nom)
    harvest_late = base_jan1 + timedelta(days=end_max)

    intervals = _phase_intervals(start_t, d_nom, phase_fracs)
    stages = _build_stages_output(base_jan1, intervals)

    return {
        "crop_id": profile.id,
        "crop_name": profile.name,
        "family": profile.family,
        "window": window_label,
        "sowing_date": sow_date.isoformat(),
        "harvest_nominal_date": harvest_nominal.isoformat(),
        "harvest_window": {
            "early_maturity": harvest_early.isoformat(),
            "nominal_maturity": harvest_nominal.isoformat(),
            "late_maturity": harvest_late.isoformat(),
        },
        "growth_cycle_days": {
            "minimum": d_min,
            "nominal": d_nom,
            "maximum": d_max,
        },
        "stages": stages,
        "kc_max": profile.kc_max,
        "delay_slack_days": delay_slack,
        "turnaround_buffer_after_days": turnaround_buffer_after,
        "safe_expiry_date": (base_jan1 + timedelta(days=safe_expiry_t)).isoformat(),
        "hard_expiry_date": (base_jan1 + timedelta(days=hard_expiry_t)).isoformat(),
        "days_until_safe_expiry": safe_expiry_t - start_t,
        "days_until_hard_expiry": hard_expiry_t - start_t,
        "collision_probability_pct": collision_prob,
        "uncertainty_cone": {
            "early_end_date": harvest_early.isoformat(),
            "nominal_end_date": harvest_nominal.isoformat(),
            "late_end_date": harvest_late.isoformat(),
            "span_days": d_max - d_min,
        },
    }


def build_direct_pair_timeline(
    p1: CropProfile,
    p2: CropProfile,
    w1: Any,
    w2: Any | None,
    s1_card: dict,
    s2_card: dict,
    trans: dict,
    *,
    ref_year: int = 2024,
    continuous: bool = False,
) -> dict[str, Any]:
    """Compute a two-crop physical timeline using direct date/day interval arithmetic."""
    base_jan1 = date(ref_year, 1, 1)
    min_buffer = 7
    optimal_buffer = 21

    # Slot 1
    s1_date, _e1_date = w1.dates(ref_year)
    start_1 = (s1_date - base_jan1).days
    d1_min, d1_nom, d1_max = _cycle_bounds_from_profile(p1)
    phase_fracs_1 = _fao_stage_fractions_from_profile(p1)
    end_1_min = start_1 + d1_min
    end_1_nom = start_1 + d1_nom
    end_1_max = start_1 + d1_max

    # Slot 2
    d2_min, d2_nom, d2_max = _cycle_bounds_from_profile(p2)
    phase_fracs_2 = _fao_stage_fractions_from_profile(p2)

    if continuous or w2 is None:
        start_2 = end_1_nom + 14
        latest_start_2 = start_2 + 21
        if w2 is not None:
            w2_label = getattr(w2, "label", "")
        else:
            s2_dt = base_jan1 + timedelta(days=start_2)
            e2_dt = base_jan1 + timedelta(days=start_2 + d2_nom)
            w2_label = f"{s2_dt:%d %b} – {e2_dt:%d %b}"
    else:
        w2_s, w2_e = w2.dates(ref_year)
        if w2_s < s1_date:
            w2_s, w2_e = w2.dates(ref_year + 1)
        w2_start_offset = (w2_s - base_jan1).days
        start_2 = max(w2_start_offset, end_1_nom + min_buffer)
        win2_len = (w2_e - w2_s).days
        latest_start_2 = _latest_start_offset(w2_start_offset, win2_len, d2_min)
        w2_label = getattr(w2, "label", "")

    turnaround_buffer_1 = start_2 - end_1_nom
    delay_slack_1 = max(0, latest_start_2 - min_buffer - d1_nom - start_1)
    safe_expiry_t_1 = latest_start_2 - min_buffer - d1_max
    hard_expiry_t_1 = latest_start_2 - min_buffer - d1_nom
    deadline_t_1 = latest_start_2 - min_buffer

    if end_1_max <= deadline_t_1:
        collision_prob_1 = 0.0
    elif end_1_min > deadline_t_1:
        collision_prob_1 = 100.0
    else:
        span_1 = max(1, end_1_max - end_1_min)
        collision_prob_1 = round(
            max(0.0, min(100.0, ((end_1_max - deadline_t_1) / span_1) * 100.0)), 1
        )

    delay_slack_2 = max(0, latest_start_2 - start_2)
    hard_expiry_t_2 = latest_start_2
    safe_expiry_t_2 = latest_start_2 - max(0, d2_max - d2_nom)

    slot_1 = _build_slot_dict(
        profile=p1,
        window_label=getattr(w1, "label", ""),
        base_jan1=base_jan1,
        start_t=start_1,
        d_min=d1_min,
        d_nom=d1_nom,
        d_max=d1_max,
        phase_fracs=phase_fracs_1,
        delay_slack=delay_slack_1,
        turnaround_buffer_after=turnaround_buffer_1,
        safe_expiry_t=safe_expiry_t_1,
        hard_expiry_t=hard_expiry_t_1,
        collision_prob=collision_prob_1,
    )
    slot_2 = _build_slot_dict(
        profile=p2,
        window_label=w2_label,
        base_jan1=base_jan1,
        start_t=start_2,
        d_min=d2_min,
        d_nom=d2_nom,
        d_max=d2_max,
        phase_fracs=phase_fracs_2,
        delay_slack=delay_slack_2,
        turnaround_buffer_after=0,
        safe_expiry_t=safe_expiry_t_2,
        hard_expiry_t=hard_expiry_t_2,
        collision_prob=0.0,
    )

    trans_status = trans.get("status", "conditional")
    hard_blocked = trans_status == "blocked"
    if hard_blocked or turnaround_buffer_1 < min_buffer:
        feasible = False
        overall_status = "blocked"
    elif turnaround_buffer_1 < optimal_buffer:
        feasible = True
        overall_status = "caution"
    elif trans_status in {"caution", "conditional"}:
        feasible = True
        overall_status = trans_status
    else:
        feasible = True
        overall_status = "complementary"

    base_util_1 = _UTILITY_MAP.get(s1_card.get("status", "unknown"), 0.0)
    base_util_2 = _UTILITY_MAP.get(s2_card.get("status", "unknown"), 0.0)
    arc_score = 15.0 if trans_status == "complementary" else (-50.0 if hard_blocked else 5.0)
    total_score = round(base_util_1 + base_util_2 + arc_score, 2)

    return {
        "overall_status": overall_status,
        "feasible": feasible,
        "total_agronomic_score": total_score,
        "safe_expiry_date": slot_1["safe_expiry_date"],
        "hard_expiry_date": slot_1["hard_expiry_date"],
        "days_until_safe_expiry": slot_1["days_until_safe_expiry"],
        "days_until_hard_expiry": slot_1["days_until_hard_expiry"],
        "collision_probability_pct": slot_1["collision_probability_pct"],
        "uncertainty_cone": {
            "slot_1_span_days": slot_1["uncertainty_cone"]["span_days"],
            "slot_2_span_days": slot_2["uncertainty_cone"]["span_days"],
            "collision_probability_pct": slot_1["collision_probability_pct"],
        },
        "turnaround_summary": _turnaround_summary(turnaround_buffer_1),
        "slots": [slot_1, slot_2],
    }
