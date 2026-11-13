"""Sequence planner and transition orchestrator."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Sequence

from agroshift.science.knowledge.knowledge import crop_by_id, global_traits, growth_stages, pest_context
from agroshift.science.decision.screening import find_options
from .contracts import CropProfile, EnvironmentContext, RotationConfig, RuleFinding, TransitionStatus
from .rules import DEFAULT_RULES, TransitionRule
from .timeline_adapter import build_physical_timeline, quantize_crop_to_activity
from .timeline_core import ArcConstraint, solve_trajectories


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

    viable = [
        cid
        for cid, c in cards_s1.items()
        if c.get("status") in {"possible", "check"} and cards_s2.get(cid, {}).get("status") in {"possible", "check"}
    ]
    if len(viable) >= 4:
        return viable[:limit]
    return list(cards_s1)[:8]


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

    if len(farm.windows) < 2:
        return []

    w1, w2 = farm.windows[0], farm.windows[1]
    farm_s1 = replace(farm, windows=(w1,), pilot_confirmed=False)
    farm_s2 = replace(farm, windows=(w2,), pilot_confirmed=False)

    cards_s1 = {c["id"]: c for c in find_options(farm_s1, dataset)}
    cards_s2 = {c["id"]: c for c in find_options(farm_s2, dataset)}

    traits_by_crop: dict[str, dict] = defaultdict(dict)
    for t in global_traits():
        if t.get("review_status") == "reviewed" and t.get("scope") == "global":
            traits_by_crop[t["crop_id"]][t["trait"]] = t

    pool = select_candidate_pool(
        cards_s1,
        cards_s2,
        candidate_crop_ids=candidate_crop_ids,
        limit=config.max_candidate_pool,
    )

    prev_crop = crop_by_id(farm.current) if farm.current not in (None, "unknown") else None
    prev_profile = CropProfile.from_crop_and_traits(prev_crop) if prev_crop else None

    profiles = {
        cid: CropProfile.from_crop_and_traits(
            crop_by_id(cid) or {"id": cid, "name": cards_s1[cid]["name"]},
            traits_by_crop.get(cid),
            growth_stages=growth_stages(cid),
            pest_records=pest_context(cid),
        )
        for cid in pool
    }

    sequences: list[dict[str, Any]] = []
    for c1_id in pool:
        for c2_id in pool:
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
                w2=w2,
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

            act1 = quantize_crop_to_activity(p1, w1, s1_card)
            act2 = quantize_crop_to_activity(p2, w2, s2_card)

            def _arc_eval(_a1: Any, _a2: Any) -> ArcConstraint:
                score = 15.0 if trans["status"] == "complementary" else (-50.0 if trans["status"] == "blocked" else 5.0)
                return ArcConstraint(
                    min_buffer=7,
                    optimal_buffer=21,
                    compatibility_score=score,
                    hard_blocked=(trans["status"] == "blocked"),
                    status=trans["status"],
                    reasons=tuple(trans["benefits"] + trans["cautions"] + trans["blockers"]),
                )

            trajs = solve_trajectories([[act1], [act2]], _arc_eval)
            timeline_data = build_physical_timeline(trajs[0]) if trajs else {}

            sequences.append(
                {
                    "id": f"{c1_id}_then_{c2_id}",
                    "name": f"{p1.name} → {p2.name}",
                    "overall_status": overall_status,
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
    sequences.sort(key=lambda r: (order_map.get(r["overall_status"], 9), r["name"].casefold()))
    return sequences[:max_sequences]
