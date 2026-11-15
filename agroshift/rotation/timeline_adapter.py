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
    if window_len > d_min:
        latest_start = start_offset + max(14, min(window_len - d_min, int(window_len * 0.45)))
    else:
        latest_start = start_offset + 14
    phase_fracs = _fao_stage_fractions_from_profile(profile)

    status = card.get("status", "unknown")
    utility_map = {"possible": 15.0, "check": 8.0, "conditional": 5.0, "outside": -10.0, "blocked": -50.0}
    base_util = utility_map.get(status, 0.0)

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

        stage_labels = [
            ("initial_emergence", "Emergence & Root Establishment"),
            ("canopy_development", "Rapid Vegetative Canopy Growth"),
            ("mid_season_flowering_peak_water", "Flowering & Peak Water Demand (Kc max)"),
            ("late_season_ripening", "Grain Fill & Ripening"),
        ]

        stages: list[dict[str, Any]] = []
        for (stage_key, stage_desc), (p_s, p_e) in zip(stage_labels, slot.phase_intervals):
            stages.append(
                {
                    "stage": stage_key,
                    "description": stage_desc,
                    "start_date": (base_jan1 + timedelta(days=p_s)).isoformat(),
                    "end_date": (base_jan1 + timedelta(days=p_e)).isoformat(),
                    "duration_days": p_e - p_s,
                }
            )

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
        "turnaround_summary": {
            "buffer_days": buffer_days,
            "status": buf_status,
            "advisory": buf_desc,
        },
        "slots": slots_output,
    }
