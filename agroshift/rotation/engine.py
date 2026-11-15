"""Sequence planner and transition orchestrator."""
from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import Any, Sequence

from agroshift.science.climate.climate import Window
from agroshift.science.knowledge.knowledge import crop_by_id, global_traits, growth_stages, pest_context
from agroshift.science.decision.screening import find_options
from .contracts import CropProfile, EnvironmentContext, RotationConfig, RuleFinding, TransitionStatus
from .rules import DEFAULT_RULES, TransitionRule
from .timeline_adapter import build_direct_pair_timeline


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


def plan_global_rotations(
    farm: Any,
    dataset: Any,
    *,
    candidate_crop_ids: list[str] | None = None,
    max_sequences: int = 16,
    config: RotationConfig = RotationConfig(),
) -> list[dict[str, Any]]:
    """Generate constraint-based two-season crop rotation plans for any location."""
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
    profiles = {
        cid: CropProfile.from_crop_and_traits(
            crop_by_id(cid) or {"id": cid, "name": cards_s1[cid]["name"]},
            traits_by_crop.get(cid),
            growth_stages=growth_stages(cid),
            pest_records=pest_context(cid),
        )
        for cid in profile_ids
    }

    sequences: list[dict[str, Any]] = []
    for c1_id in c1_pool:
        for c2_id in c2_pool:
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

            sequences.append(
                {
                    "id": f"{c1_id}_then_{c2_id}",
                    "name": f"{p1.name} → {p2.name}",
                    "overall_status": overall_status,
                    "score": rating_info["score"],
                    "rating": rating_info["rating"],
                    "components": rating_info["components"],
                    "easiness_matrix": easiness_matrix,
                    "ease_adjusted_score": ease_adjusted_score,
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
            )

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
