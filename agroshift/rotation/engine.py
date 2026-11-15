"""Sequence planner and transition orchestrator."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from typing import Any, Sequence

from agroshift.science.climate.climate import Window
from agroshift.science.knowledge.knowledge import crop_by_id, global_traits, growth_stages, pest_context
from agroshift.science.decision.screening import find_options
from .contracts import CropProfile, EnvironmentContext, RotationConfig, RuleFinding, TransitionStatus
from .rules import DEFAULT_RULES, TransitionRule
from .timeline_adapter import (
    _build_slot_dict,
    _cycle_bounds_from_profile,
    _fao_stage_fractions_from_profile,
    build_direct_pair_timeline,
)


def evaluate_transition(
    first_crop: dict | CropProfile,
    second_crop: dict | CropProfile,
    *,
    previous_crop: dict | CropProfile | None = None,
    first_traits: dict | None = None,
    second_traits: dict | None = None,
    w1: Any = None,
    w2: Any = None,
    config: RotationConfig = RotationConfig(),
    rules: Sequence[TransitionRule] = DEFAULT_RULES,
    env: EnvironmentContext | None = None,
) -> dict[str, Any]:
    """Evaluate consecutive crop transition using composable agronomic rules."""
    p1 = (
        first_crop
        if isinstance(first_crop, CropProfile)
        else CropProfile.from_crop_and_traits(first_crop, first_traits)
    )
    p2 = (
        second_crop
        if isinstance(second_crop, CropProfile)
        else CropProfile.from_crop_and_traits(second_crop, second_traits)
    )
    prev = (
        previous_crop
        if isinstance(previous_crop, CropProfile) or previous_crop is None
        else CropProfile.from_crop_and_traits(previous_crop)
    )

    findings: list[RuleFinding] = []
    for rule in rules:
        try:
            findings.extend(rule(p1, p2, prev, w1, w2, config, env))
        except TypeError:
            findings.extend(rule(p1, p2, prev, w1, w2, config))
    blockers = [f.message for f in findings if f.severity == "blocker"]
    cautions = [f.message for f in findings if f.severity == "caution"]
    benefits = [f.message for f in findings if f.severity == "benefit"]

    if blockers:
        status: TransitionStatus = "blocked"
        summary = "Blocked by life-cycle or calendar overlap"
    elif any(f.rule_id == "same_family_s1_s2" for f in findings):
        status = "caution"
        summary = "Same-family succession caution"
    elif cautions:
        status = "conditional"
        summary = "Feasible with management checks"
    else:
        status = "complementary"
        summary = "Complementary botanical rotation"

    return {
        "status": status,
        "summary": summary,
        "first_crop_id": p1.id,
        "first_crop_name": p1.name,
        "first_family": p1.family,
        "second_crop_id": p2.id,
        "second_crop_name": p2.name,
        "second_family": p2.family,
        "blockers": blockers,
        "cautions": cautions,
        "benefits": benefits,
        "findings": [asdict(f) for f in findings],
        "scientific_disclaimer": (
            "Rotation checks evaluate botanical family alternation, life-cycle compatibility, window turnaround, "
            "and rooting depth references. Exact nitrogen fixation (kg/ha) or disease-suppression percentages "
            "are not fabricated without site-specific trial measurements."
        ),
    }


def select_candidate_pool(
    cards_s1: dict[str, dict[str, Any]],
    cards_s2: dict[str, dict[str, Any]],
    *,
    candidate_crop_ids: Sequence[str] | None = None,
    limit: int = 10,
) -> list[str]:
    """Deterministically rank and select crop candidate pool for rotation pairing."""
    if candidate_crop_ids is not None:
        return [cid for cid in candidate_crop_ids if cid in cards_s1 and cid in cards_s2]

    rank_score = {"possible": 0, "check": 1, "outside": 2, "unknown": 3, "blocked": 4}
    both_viable = [
        cid
        for cid, c in cards_s1.items()
        if c.get("status") in {"possible", "check"} and cards_s2.get(cid, {}).get("status") in {"possible", "check"}
    ]
    both_viable.sort(
        key=lambda cid: (
            rank_score.get(cards_s1[cid].get("status"), 9) + rank_score.get(cards_s2[cid].get("status"), 9),
            cid,
        )
    )
    either_viable = [
        cid
        for cid in cards_s1
        if cid not in both_viable
        and (
            cards_s1[cid].get("status") in {"possible", "check"}
            or cards_s2.get(cid, {}).get("status") in {"possible", "check"}
        )
    ]
    either_viable.sort(
        key=lambda cid: (
            min(
                rank_score.get(cards_s1[cid].get("status"), 9),
                rank_score.get(cards_s2[cid].get("status"), 9),
            ),
            cid,
        )
    )
    viable = both_viable + either_viable
    if viable:
        return viable[:limit]
    return list(cards_s1)[:8]

def rate_rotation_sequence(
    s1_card: dict[str, Any],
    s2_card: dict[str, Any],
    transition: dict[str, Any],
    timeline: dict[str, Any],
) -> dict[str, Any]:
    """Compute a multi-criteria agronomic score (0-100) and rating tier for a rotation."""
    def _card_pts(card: dict[str, Any]) -> float:
        st = card.get("status")
        if st == "possible":
            return 20.0
        if st == "check":
            return 12.0
        if st == "outside":
            return 5.0
        return 0.0

    climate_pts = _card_pts(s1_card) + _card_pts(s2_card)

    trans_status = transition.get("status", "conditional")
    if trans_status == "blocked":
        trans_pts = 0.0
    else:
        trans_pts = 15.0
        findings = transition.get("findings", [])
        for f in findings:
            sev = f.get("severity")
            if sev == "benefit":
                trans_pts += 6.0
            elif sev == "caution":
                trans_pts -= 7.0
            elif sev == "blocker":
                trans_pts -= 15.0
        trans_pts = max(0.0, min(35.0, trans_pts))

    tb = timeline.get("turnaround_summary", {})
    buf_status = tb.get("status")
    if buf_status == "optimal":
        time_pts = 20.0
    elif buf_status == "acceptable":
        time_pts = 16.0
    elif buf_status == "tight":
        time_pts = 6.0
    elif buf_status == "excessive_fallow":
        time_pts = 10.0
    elif buf_status == "collision":
        time_pts = 0.0
    else:
        time_pts = 14.0

    slots = timeline.get("slots", [])
    slack_bonus = sum(2.5 for s in slots if s.get("delay_slack_days", 0) > 0)
    span_total = sum(s.get("uncertainty_cone", {}).get("span_days", 0) for s in slots)
    span_penalty = min(6.0, max(0.0, (span_total - 20) * 0.06))
    coll_prob = float(timeline.get("collision_probability_pct", 0.0) or 0.0)
    coll_penalty = min(6.0, coll_prob * 0.1)
    time_pts = max(0.0, min(25.0, time_pts + slack_bonus - span_penalty - coll_penalty))

    total = round(climate_pts + trans_pts + time_pts, 1)
    if total >= 88.0:
        tier = "Excellent"
    elif total >= 72.0:
        tier = "Good"
    elif total >= 52.0:
        tier = "Moderate"
    else:
        tier = "Restricted"

    return {
        "score": total,
        "rating": tier,
        "components": {
            "climate_suitability": round(climate_pts, 1),
            "transition_synergy": round(trans_pts, 1),
            "timeline_efficiency": round(time_pts, 1),
        },
    }


def _clamp_0_10(val: float) -> float:
    return round(max(0.0, min(10.0, float(val))), 2)


def compute_easiness_matrix(
    s1_card: dict[str, Any],
    s2_card: dict[str, Any],
    p1: CropProfile,
    p2: CropProfile,
    transition: dict[str, Any],
    timeline: dict[str, Any],
    env: EnvironmentContext | None = None,
) -> dict[str, Any]:
    """Compute a 0.0-10.0 Easiness Score (10 - hardness) across 5 physical operational factors."""
    findings = transition.get("findings", [])
    finding_ids = {f.get("rule_id") for f in findings}

    # 1. turnaround_expiry_pressure (0-10 hardness)
    tb = timeline.get("turnaround_summary", {})
    buffer_days = tb.get("buffer_days", 14)
    slots = timeline.get("slots", [])
    delay_slack = slots[0].get("delay_slack_days", 14) if slots else 14
    collision_pct = float(timeline.get("collision_probability_pct", 0.0) or 0.0)

    if buffer_days < 0:
        f1 = 6.0
    elif buffer_days < 7:
        f1 = 4.5
    elif buffer_days < 14:
        f1 = 2.5
    elif buffer_days <= 35:
        f1 = 0.5
    else:
        f1 = 1.5

    if delay_slack <= 0:
        f1 += 2.0
    elif delay_slack < 7:
        f1 += 1.0
    f1 += (collision_pct / 100.0) * 3.0
    f1 = _clamp_0_10(f1)

    # 2. earthwork_drainage_flip (0-10 hardness)
    f2 = 1.0
    first_conflict = p1.trait_value("persistent_waterlogging_conflict")
    is_paddy_flip = (
        "drainage_transition" in finding_ids
        or (p1.id == "rice" and p2.id != "rice")
        or (first_conflict is False and p2.waterlogging_sensitive)
    )
    if is_paddy_flip:
        f2 += 6.0
    if env is not None:
        if env.slope_pct is not None:
            if env.slope_pct >= 15.0:
                f2 += 3.0
            elif env.slope_pct >= 8.0:
                f2 += 1.5
            elif env.slope_pct >= 4.0:
                f2 += 0.5
        if env.drainage in {"poor", "very_poor"} and p2.waterlogging_sensitive:
            f2 += 2.0
    f2 = _clamp_0_10(f2)

    # 3. water_irrigation_dependency (0-10 hardness)
    f3 = 1.0
    kc1 = p1.kc_max if p1.kc_max is not None else 1.0
    kc2 = p2.kc_max if p2.kc_max is not None else 1.0
    avg_kc = 0.5 * (kc1 + kc2)
    if avg_kc >= 1.15:
        f3 += 2.5
    elif avg_kc >= 1.0:
        f3 += 1.5

    irrig = env.irrigation if env is not None else "unknown"
    if irrig == "rainfed":
        if "water_deficit_carryover" in finding_ids:
            f3 += 2.5
        if env is not None and env.rainfall_s1_mm is not None and env.water_need_s1_mm:
            deficit_ratio = max(0.0, (env.water_need_s1_mm - env.rainfall_s1_mm) / env.water_need_s1_mm)
            f3 += min(4.0, deficit_ratio * 6.0)
        elif s1_card.get("status") == "check" or s2_card.get("status") == "check":
            f3 += 2.0
    elif irrig == "unknown":
        f3 += 1.5
    elif irrig in {"reliable", "irrigated"}:
        f3 += 0.5
    f3 = _clamp_0_10(f3)

    # 4. soil_nutrient_intervention (0-10 hardness)
    f4 = 3.0
    if p1.is_nitrogen_fixer or p2.is_nitrogen_fixer:
        f4 -= 2.0
    if p1.nutrient_demand == "heavy" and p2.nutrient_demand == "heavy":
        f4 += 4.0
    elif p1.nutrient_demand == "heavy" or p2.nutrient_demand == "heavy":
        f4 += 1.5
    if env is not None and env.soil_ph is not None:
        if env.soil_ph < 5.5 or env.soil_ph > 8.0:
            f4 += 2.5
        elif env.soil_ph < 5.8 or env.soil_ph > 7.6:
            f4 += 1.0
    if s1_card.get("status") == "check" or s2_card.get("status") == "check":
        f4 += 0.5
    f4 = _clamp_0_10(f4)

    # 5. pest_pathogen_vigilance (0-10 hardness)
    f5 = 1.5
    n_shared = len(p1.pests & p2.pests) if (p1.pests and p2.pests) else 0
    if n_shared > 0:
        f5 += min(5.0, 2.5 + n_shared * 1.0)
    if p1.family and p2.family and p1.family == p2.family:
        f5 += 3.5
    elif p1.family and p2.family and p1.family != p2.family and n_shared == 0:
        f5 -= 1.0
    f5 = _clamp_0_10(f5)

    factors = {
        "turnaround_expiry_pressure": f1,
        "earthwork_drainage_flip": f2,
        "water_irrigation_dependency": f3,
        "soil_nutrient_intervention": f4,
        "pest_pathogen_vigilance": f5,
    }
    hardness_score = round(sum(factors.values()) / 5.0, 2)
    easiness_score = round(10.0 - hardness_score, 2)

    if easiness_score >= 7.5:
        easiness_tier = "Easy"
    elif easiness_score >= 5.5:
        easiness_tier = "Moderate"
    elif easiness_score >= 3.5:
        easiness_tier = "Demanding"
    else:
        easiness_tier = "Hard"

    return {
        "easiness_score": easiness_score,
        "hardness_score": hardness_score,
        "easiness_tier": easiness_tier,
        "factors": factors,
    }


def _pick_followup_crop_id(
    prev_id: str,
    used_ids: set[str],
    used_families: set[str],
    follow_pool: Sequence[str],
    profiles: dict[str, CropProfile],
    cards_s2: dict[str, dict[str, Any]],
    cards_s1: dict[str, dict[str, Any]],
) -> str:
    """Select the best follow-up crop ID preferring non-repeat, family break, and viability."""
    if not follow_pool:
        return prev_id
    prev_profile = profiles[prev_id]
    prev_family = prev_profile.family

    def _rank_key(item: tuple[int, str]) -> tuple[int, int, int, int, int, int, int, int, int]:
        idx, cid = item
        p = profiles[cid]
        card = cards_s2.get(cid) or cards_s1.get(cid) or {}
        status = card.get("status")
        viable_rank = 0 if status in {"possible", "check"} else 1
        exact_status_rank = 0 if status == "possible" else (1 if status == "check" else 2)
        return (
            0 if cid != prev_id else 1,
            0 if p.life_cycle != "perennial" else 1,
            viable_rank,
            0 if (p.family and prev_family and p.family != prev_family) else 1,
            0 if cid not in used_ids else 1,
            0 if (p.family and p.family not in used_families) else 1,
            0 if (p.is_nitrogen_fixer and prev_profile.nutrient_demand == "heavy") else 1,
            exact_status_rank,
            idx,
        )

    _, best_id = min(enumerate(follow_pool), key=_rank_key)
    return best_id


def _extend_timeline_with_followup_crops(
    timeline_data: dict[str, Any],
    *,
    c1_id: str,
    c2_id: str,
    follow_pool: Sequence[str],
    profiles: dict[str, CropProfile],
    cards_s1: dict[str, dict[str, Any]],
    cards_s2: dict[str, dict[str, Any]],
    include_fourth: bool = False,
    target_slots: int | None = None,
    monocrop_mode: bool = False,
    turnaround_days: int = 14,
    ref_year: int = 2024,
) -> None:
    """Extend a 2-slot timeline in-place with Slot 3 and optional Slot 4 crops."""
    want_fourth = (target_slots >= 4) if target_slots is not None else include_fourth
    if monocrop_mode:
        followup_ids = [c1_id]
    else:
        used_ids: set[str] = {c1_id, c2_id}
        used_families: set[str] = {
            f for f in (profiles[c1_id].family, profiles[c2_id].family) if f
        }
        c3_id = _pick_followup_crop_id(
            c2_id, used_ids, used_families, follow_pool, profiles, cards_s2, cards_s1
        )
        followup_ids = [c3_id]
        if want_fourth:
            used_ids.add(c3_id)
            if profiles[c3_id].family:
                used_families.add(profiles[c3_id].family)
            c4_id = _pick_followup_crop_id(
                c3_id, used_ids, used_families, follow_pool, profiles, cards_s2, cards_s1
            )
            followup_ids.append(c4_id)

    base_jan1 = date(ref_year, 1, 1)
    min_buffer = 7
    slots: list[dict[str, Any]] = timeline_data["slots"]

    for idx, next_id in enumerate(followup_ids):
        is_last = idx == len(followup_ids) - 1
        prev_slot = slots[-1]
        prev_slot["turnaround_buffer_after_days"] = turnaround_days

        prev_harvest = date.fromisoformat(prev_slot["harvest_nominal_date"])
        sowing_date = prev_harvest + timedelta(days=turnaround_days)
        start_t = (sowing_date - base_jan1).days

        p_next = profiles[next_id]
        d_min, d_nom, d_max = _cycle_bounds_from_profile(p_next)
        phase_fracs = _fao_stage_fractions_from_profile(p_next)
        s_dt = base_jan1 + timedelta(days=start_t)
        e_dt = base_jan1 + timedelta(days=start_t + d_nom)
        window_label = f"{s_dt:%d %b} – {e_dt:%d %b}"

        if not is_last:
            latest_next_start = start_t + d_nom + turnaround_days + 21
            deadline_t = latest_next_start - min_buffer
            delay_slack = max(0, deadline_t - d_nom - start_t)
            safe_expiry_t = deadline_t - d_max
            hard_expiry_t = deadline_t - d_nom
            turnaround_after = turnaround_days
        else:
            latest_start = start_t + 21
            delay_slack = max(0, latest_start - start_t)
            hard_expiry_t = latest_start
            safe_expiry_t = latest_start - max(0, d_max - d_nom)
            turnaround_after = 0

        slots.append(
            _build_slot_dict(
                profile=p_next,
                window_label=window_label,
                base_jan1=base_jan1,
                start_t=start_t,
                d_min=d_min,
                d_nom=d_nom,
                d_max=d_max,
                phase_fracs=phase_fracs,
                delay_slack=delay_slack,
                turnaround_buffer_after=turnaround_after,
                safe_expiry_t=safe_expiry_t,
                hard_expiry_t=hard_expiry_t,
                collision_prob=0.0,
            )
        )


def _ensure_profile(
    cid: str,
    profiles: dict[str, CropProfile],
    cards_s1: dict[str, dict[str, Any]],
    traits_by_crop: dict[str, dict],
) -> None:
    """Populate a CropProfile into `profiles` if not already loaded."""
    if cid not in profiles:
        profiles[cid] = CropProfile.from_crop_and_traits(
            crop_by_id(cid) or {"id": cid, "name": cards_s1[cid]["name"]},
            traits_by_crop.get(cid),
            growth_stages=growth_stages(cid),
            pest_records=pest_context(cid),
        )


def _compute_filter_scores(
    rating_info: dict[str, Any],
    easiness_matrix: dict[str, Any],
    ease_adjusted_score: float,
) -> dict[str, float]:
    """Compute 0-100 per-goal filter scores from rating components and easiness factors."""
    factors = easiness_matrix["factors"]
    f_water = float(factors.get("water_irrigation_dependency", 5.0))
    f_soil = float(factors.get("soil_nutrient_intervention", 5.0))
    f_pest = float(factors.get("pest_pathogen_vigilance", 5.0))
    clim = float(rating_info["components"].get("climate_suitability", 25.0))
    syn = float(rating_info["components"].get("transition_synergy", 20.0))
    return {
        "default": round(float(rating_info["score"]), 1),
        "water": round(min(100.0, max(0.0, (10.0 - f_water) * 6.5 + clim * 0.85)), 1),
        "soil": round(min(100.0, max(0.0, (10.0 - f_soil) * 6.5 + syn * 1.0)), 1),
        "pest": round(min(100.0, max(0.0, (10.0 - f_pest) * 6.5 + syn * 1.0)), 1),
        "ease": round(min(100.0, max(0.0, float(ease_adjusted_score))), 1),
    }


def _build_scored_sequence(
    c1_id: str,
    c2_id: str,
    *,
    profiles: dict[str, CropProfile],
    cards_s1: dict[str, dict[str, Any]],
    cards_s2: dict[str, dict[str, Any]],
    farm: Any,
    prev_profile: CropProfile | None,
    w1: Window,
    w2: Window,
    continuous: bool,
    config: RotationConfig,
    is_custom: bool = False,
) -> dict[str, Any]:
    """Evaluate and score a 2-crop rotation pair into a sequence dict."""
    p1 = profiles[c1_id]
    p2 = profiles[c2_id]
    s1_card = cards_s1[c1_id]
    s2_card = cards_s2[c2_id]

    w1_info = s1_card.get("water") if isinstance(s1_card.get("water"), dict) else {}
    w2_info = s2_card.get("water") if isinstance(s2_card.get("water"), dict) else {}
    env = EnvironmentContext(
        drainage=getattr(farm, "drainage", "unknown") or "unknown",
        soil_texture=getattr(farm, "soil_type", "unknown") or "unknown",
        soil_ph=getattr(farm, "ph", None),
        slope_pct=getattr(farm, "slope", None),
        irrigation=getattr(farm, "irrigation", "unknown") or "unknown",
        rainfall_s1_mm=w1_info.get("rainfall_mm"),
        water_need_s1_mm=w1_info.get("water_need_mm"),
        water_need_s2_mm=w2_info.get("water_need_mm"),
    )

    trans = evaluate_transition(
        p1,
        p2,
        previous_crop=prev_profile,
        w1=w1,
        w2=None if continuous else w2,
        config=config,
        env=env,
    )

    slot_blocked = s1_card["status"] == "blocked" or s2_card["status"] == "blocked" or trans["status"] == "blocked"
    if slot_blocked:
        overall_status = "blocked"
    elif s1_card["status"] == "outside" or s2_card["status"] == "outside":
        overall_status = "outside"
    elif trans["status"] == "caution":
        overall_status = "caution"
    elif s1_card["status"] == "possible" and s2_card["status"] == "possible" and trans["status"] == "complementary":
        overall_status = "complementary"
    else:
        overall_status = "conditional"

    timeline_data = build_direct_pair_timeline(
        p1,
        p2,
        w1,
        w2,
        s1_card,
        s2_card,
        trans,
        continuous=continuous,
    )

    rating_info = rate_rotation_sequence(s1_card, s2_card, trans, timeline_data)
    easiness_matrix = compute_easiness_matrix(
        s1_card, s2_card, p1, p2, trans, timeline_data, env
    )
    ease_adjusted_score = round(
        0.65 * rating_info["score"] + 3.5 * easiness_matrix["easiness_score"], 1
    )
    filter_scores = _compute_filter_scores(rating_info, easiness_matrix, ease_adjusted_score)

    return {
        "id": f"{c1_id}_then_{c2_id}",
        "name": f"{p1.name} → {p2.name}",
        "overall_status": overall_status,
        "score": rating_info["score"],
        "rating": rating_info["rating"],
        "components": rating_info["components"],
        "easiness_matrix": easiness_matrix,
        "ease_adjusted_score": ease_adjusted_score,
        "filter_scores": filter_scores,
        "is_custom": is_custom,
        "summary": trans["summary"],
        "season_1": {
            "window": w1.label,
            "crop_id": c1_id,
            "crop_name": p1.name,
            "family": p1.family,
            "status": s1_card["status"],
            "reason": s1_card.get("reason", ""),
            "water": s1_card.get("water", {}),
        },
        "season_2": {
            "window": w2.label,
            "crop_id": c2_id,
            "crop_name": p2.name,
            "family": p2.family,
            "status": s2_card["status"],
            "reason": s2_card.get("reason", ""),
            "water": s2_card.get("water", {}),
        },
        "transition": trans,
        "timeline": timeline_data,
    }


def _build_custom_sequence(
    valid_custom_ids: list[str],
    *,
    pinned_c1: str | None,
    pool: list[str],
    follow_pool: list[str],
    profiles: dict[str, CropProfile],
    cards_s1: dict[str, dict[str, Any]],
    cards_s2: dict[str, dict[str, Any]],
    traits_by_crop: dict[str, dict],
    farm: Any,
    prev_profile: CropProfile | None,
    w1: Window,
    w2: Window,
    continuous: bool,
    config: RotationConfig,
    monocrop_strategy: bool,
    top_regional: dict[str, Any] | None,
    order_map: dict[str, int],
) -> dict[str, Any]:
    """Score the best rotation ordering of `valid_custom_ids` with gap comparison and smart swap."""
    for cid in valid_custom_ids:
        _ensure_profile(cid, profiles, cards_s1, traits_by_crop)

    if pinned_c1 and pinned_c1 in cards_s1:
        c2_candidates = [cid for cid in valid_custom_ids if cid != pinned_c1] or valid_custom_ids
        candidate_pairs = [(pinned_c1, c2_id) for c2_id in c2_candidates]
    elif len(valid_custom_ids) >= 2:
        candidate_pairs = [
            (c1_id, c2_id)
            for c1_id in valid_custom_ids
            for c2_id in valid_custom_ids
            if c1_id != c2_id
        ]
    else:
        candidate_pairs = [(valid_custom_ids[0], valid_custom_ids[0])]

    custom_sequences = [
        _build_scored_sequence(
            c1_id,
            c2_id,
            profiles=profiles,
            cards_s1=cards_s1,
            cards_s2=cards_s2,
            farm=farm,
            prev_profile=prev_profile,
            w1=w1,
            w2=w2,
            continuous=continuous,
            config=config,
            is_custom=True,
        )
        for c1_id, c2_id in candidate_pairs
    ]
    custom_sequences.sort(
        key=lambda r: (
            -r["score"],
            order_map.get(r["overall_status"], 9),
            r["name"].casefold(),
        )
    )
    best_custom = custom_sequences[0]

    custom_follow_pool = list(dict.fromkeys(list(valid_custom_ids) + follow_pool))
    target_slots = min(4, max(3, len(valid_custom_ids)))
    _extend_timeline_with_followup_crops(
        best_custom["timeline"],
        c1_id=best_custom["season_1"]["crop_id"],
        c2_id=best_custom["season_2"]["crop_id"],
        follow_pool=custom_follow_pool,
        profiles=profiles,
        cards_s1=cards_s1,
        cards_s2=cards_s2,
        target_slots=target_slots,
        monocrop_mode=monocrop_strategy,
    )
    best_custom["id"] = "custom_" + "_".join(s["crop_id"] for s in best_custom["timeline"]["slots"])
    best_custom["name"] = " → ".join(s["crop_name"] for s in best_custom["timeline"]["slots"])
    best_custom["is_custom"] = True

    if top_regional is not None:
        gap_pts = round(best_custom["score"] - top_regional["score"], 1)
    else:
        gap_pts = 0.0

    if gap_pts >= 0:
        reason = "★ Matches or beats top regional rotation"
    else:
        c_factors = best_custom["easiness_matrix"]["factors"]
        f_pest = float(c_factors.get("pest_pathogen_vigilance", 5.0))
        f_water = float(c_factors.get("water_irrigation_dependency", 5.0))
        f_soil = float(c_factors.get("soil_nutrient_intervention", 5.0))
        if best_custom["transition"]["status"] in ("caution", "blocked") or f_pest >= 4.0:
            reason = "Same-family or shared pest risk lowers score"
        elif f_water >= 4.5:
            reason = "Higher water demand in dry window"
        elif f_soil >= 4.5:
            reason = "Heavy nutrient demand without legume fixer"
        else:
            reason = "Lower seasonal climate fit than #1 regional plan"
    best_custom["custom_comparison"] = {"gap_pts": gap_pts, "reason": reason}

    c1_id = best_custom["season_1"]["crop_id"]
    c2_id = best_custom["season_2"]["crop_id"]
    replace_slot_1 = bool(not pinned_c1 and cards_s1[c1_id]["status"] != "possible")
    weak_cid = c1_id if replace_slot_1 else c2_id

    custom_set = set(valid_custom_ids)
    swap_candidates = [
        cid for cid in pool if cid not in custom_set and cid in cards_s1 and cid in cards_s2
    ]
    best_rep_cid: str | None = None
    best_alt_score = best_custom["score"]
    for rep_cid in swap_candidates:
        _ensure_profile(rep_cid, profiles, cards_s1, traits_by_crop)
        alt_c1 = rep_cid if replace_slot_1 else c1_id
        alt_c2 = c2_id if replace_slot_1 else rep_cid
        alt_seq = _build_scored_sequence(
            alt_c1,
            alt_c2,
            profiles=profiles,
            cards_s1=cards_s1,
            cards_s2=cards_s2,
            farm=farm,
            prev_profile=prev_profile,
            w1=w1,
            w2=w2,
            continuous=continuous,
            config=config,
            is_custom=True,
        )
        if alt_seq["score"] > best_alt_score:
            best_alt_score = alt_seq["score"]
            best_rep_cid = rep_cid

    if best_rep_cid is not None:
        gain_pts = round(best_alt_score - best_custom["score"], 1)
        if gain_pts >= 2.0:
            best_custom["smart_swap"] = {
                "replace_crop_id": weak_cid,
                "replace_crop_name": profiles[weak_cid].name,
                "with_crop_id": best_rep_cid,
                "with_crop_name": profiles[best_rep_cid].name,
                "gain_pts": gain_pts,
                "reason": (
                    "Fixes soil nitrogen"
                    if profiles[best_rep_cid].is_nitrogen_fixer
                    else "Better climate & family fit"
                ),
            }

    return best_custom


def plan_global_rotations(
    farm: Any,
    dataset: Any,
    *,
    candidate_crop_ids: list[str] | None = None,
    custom_crop_ids: Sequence[str] | None = None,
    max_sequences: int = 16,
    config: RotationConfig = RotationConfig(),
    strategy: str | None = None,
) -> list[dict[str, Any]]:
    """Generate constraint-based multi-crop rotation plans (3–4 slots) for any location."""
    from collections import defaultdict
    from dataclasses import replace

    if len(farm.windows) >= 2:
        w1, w2 = farm.windows[0], farm.windows[1]
        continuous = False
    else:
        w1 = farm.windows[0] if len(farm.windows) == 1 else Window(4, 1, 7, 31)
        continuous = True
        _, w1_end = w1.dates(2023)
        w2_start = w1_end + timedelta(days=14)
        w2_end = w2_start + timedelta(days=120)
        w2 = Window(w2_start.month, w2_start.day, w2_end.month, w2_end.day)

    farm_s1 = replace(farm, windows=(w1,), pilot_confirmed=False)
    farm_s2 = replace(farm, windows=(w2,), pilot_confirmed=False)

    cards_s1 = {c["id"]: c for c in find_options(farm_s1, dataset)}
    cards_s2 = {c["id"]: c for c in find_options(farm_s2, dataset)}

    traits_by_crop: dict[str, dict] = defaultdict(dict)
    for t in global_traits():
        if t.get("review_status") == "reviewed" and t.get("scope") == "global":
            traits_by_crop[t["crop_id"]][t["trait"]] = t

    pinned_c1 = (
        candidate_crop_ids[0]
        if candidate_crop_ids is not None and len(candidate_crop_ids) == 1
        else (
            farm.current
            if getattr(farm, "current", "unknown") not in (None, "unknown") and candidate_crop_ids is None
            else None
        )
    )

    pool = select_candidate_pool(
        cards_s1,
        cards_s2,
        candidate_crop_ids=candidate_crop_ids if (candidate_crop_ids and len(candidate_crop_ids) > 1) else None,
        limit=config.max_candidate_pool,
    )

    prev_crop = (
        crop_by_id(farm.current)
        if getattr(farm, "current", "unknown") not in (None, "unknown") and pinned_c1 != farm.current
        else None
    )
    prev_profile = CropProfile.from_crop_and_traits(prev_crop) if prev_crop else None

    if pinned_c1 and pinned_c1 in cards_s1:
        c1_pool = [pinned_c1]
        s2_rank = {"possible": 0, "check": 1, "outside": 2, "unknown": 3, "blocked": 4}
        s2_viable = [
            cid
            for cid, card in cards_s2.items()
            if cid != pinned_c1 and card.get("status") in {"possible", "check"}
        ]
        s2_viable.sort(
            key=lambda cid: (s2_rank.get(cards_s2[cid].get("status"), 9), cid)
        )
        if s2_viable:
            c2_pool = s2_viable[: config.max_candidate_pool]
        else:
            c2_pool = [cid for cid in pool if cid != pinned_c1] or pool
    else:
        c1_pool = pool
        c2_pool = pool

    profile_ids = list(dict.fromkeys(c1_pool + c2_pool))
    profiles: dict[str, CropProfile] = {}
    for cid in profile_ids:
        _ensure_profile(cid, profiles, cards_s1, traits_by_crop)

    follow_pool = list(dict.fromkeys(c2_pool + c1_pool))
    monocrop_strategy = (
        strategy == "continuous" or getattr(farm, "strategy", None) == "continuous"
    )

    sequences: list[dict[str, Any]] = [
        _build_scored_sequence(
            c1_id,
            c2_id,
            profiles=profiles,
            cards_s1=cards_s1,
            cards_s2=cards_s2,
            farm=farm,
            prev_profile=prev_profile,
            w1=w1,
            w2=w2,
            continuous=continuous,
            config=config,
            is_custom=False,
        )
        for c1_id in c1_pool
        for c2_id in c2_pool
    ]

    order_map = {"complementary": 0, "conditional": 1, "caution": 2, "outside": 3, "blocked": 4}
    sequences.sort(
        key=lambda r: (
            order_map.get(r["overall_status"], 9),
            -r["score"],
            r["name"].casefold(),
        )
    )
    for idx, seq in enumerate(sequences, start=1):
        seq["rank"] = idx

    result = sequences[:max_sequences]
    for idx, seq in enumerate(result, start=1):
        _extend_timeline_with_followup_crops(
            seq["timeline"],
            c1_id=seq["season_1"]["crop_id"],
            c2_id=seq["season_2"]["crop_id"],
            follow_pool=follow_pool,
            profiles=profiles,
            cards_s1=cards_s1,
            cards_s2=cards_s2,
            include_fourth=(idx % 2 == 0) and not monocrop_strategy,
            monocrop_mode=monocrop_strategy,
        )
        seq["name"] = " → ".join(s["crop_name"] for s in seq["timeline"]["slots"])

    valid_custom_ids = (
        list(
            dict.fromkeys(
                cid
                for cid in custom_crop_ids
                if isinstance(cid, str) and cid in cards_s1 and cid in cards_s2
            )
        )
        if isinstance(custom_crop_ids, Sequence) and not isinstance(custom_crop_ids, (str, bytes))
        else []
    )
    if valid_custom_ids:
        best_custom = _build_custom_sequence(
            valid_custom_ids,
            pinned_c1=pinned_c1,
            pool=pool,
            follow_pool=follow_pool,
            profiles=profiles,
            cards_s1=cards_s1,
            cards_s2=cards_s2,
            traits_by_crop=traits_by_crop,
            farm=farm,
            prev_profile=prev_profile,
            w1=w1,
            w2=w2,
            continuous=continuous,
            config=config,
            monocrop_strategy=monocrop_strategy,
            top_regional=result[0] if result else None,
            order_map=order_map,
        )
        result.append(best_custom)
        result.sort(
            key=lambda r: (
                -r["score"],
                order_map.get(r["overall_status"], 9),
                r["name"].casefold(),
            )
        )
        for idx, seq in enumerate(result, start=1):
            seq["rank"] = idx

    ease_sorted = sorted(
        result,
        key=lambda r: (
            order_map.get(r["overall_status"], 9),
            -r["ease_adjusted_score"],
            r["name"].casefold(),
        ),
    )
    for idx, seq in enumerate(ease_sorted, start=1):
        seq["ease_rank"] = idx

    return result
