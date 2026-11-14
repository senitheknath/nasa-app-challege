"""Constraint-based international crop rotation and multi-season sequence planner."""
from __future__ import annotations

from collections import defaultdict

from .knowledge import crop_by_id, global_traits
from .screening import find_options


def _window_overlap_days(w1, w2) -> int:
    """Check whether two recurring seasonal windows overlap within a 12-month cycle."""
    s1, e1 = w1.dates(2023)
    s2, e2 = w2.dates(2023)
    if s2 < s1:
        s2, e2 = w2.dates(2024)
    overlap_start = max(s1, s2)
    overlap_end = min(e1, e2)
    return max(0, (overlap_end - overlap_start).days + 1)


def evaluate_transition(
    first_crop: dict,
    second_crop: dict,
    *,
    previous_crop: dict | None = None,
    first_traits: dict | None = None,
    second_traits: dict | None = None,
    w1=None,
    w2=None,
) -> dict:
    """Evaluate botanical family, life-cycle, rooting-depth, and drainage transitions between consecutive crops."""
    f_fam = first_crop.get("family")
    s_fam = second_crop.get("family")
    p_fam = (previous_crop or {}).get("family")
    f_cycle = first_crop.get("life_cycle") or "annual"
    s_cycle = second_crop.get("life_cycle") or "annual"

    blockers = []
    cautions = []
    benefits = []

    # 1. Life-cycle check (annual vs perennial)
    if f_cycle == "perennial":
        blockers.append(
            f"{first_crop['name']} is a perennial crop and occupies the field across multiple seasons; "
            f"it cannot be rotated into {second_crop['name']} within a single annual two-season cycle."
        )
    if s_cycle == "perennial":
        cautions.append(
            f"{second_crop['name']} is a perennial crop; planting it in Season 2 commits the field beyond the current year."
        )

    # 2. Window overlap and turnaround check
    if w1 is not None and w2 is not None:
        overlap = _window_overlap_days(w1, w2)
        if overlap > 0:
            blockers.append(
                f"Season 1 ({w1.label}) and Season 2 ({w2.label}) overlap by {overlap} days, leaving no turnaround time for harvest and land preparation."
            )

    # 3. Botanical family succession & pest/disease bridge check
    if f_fam and s_fam:
        if f_fam == s_fam:
            cautions.append(
                f"Both Season 1 ({first_crop['name']}) and Season 2 ({second_crop['name']}) belong to {f_fam}; "
                "consecutive same-family planting increases host-specific pest, disease, and weed carryover."
            )
        elif "Fabaceae" in (f_fam, s_fam):
            benefits.append(
                f"Alternates {f_fam} ({first_crop['name']}) with {s_fam} ({second_crop['name']}), "
                "including a leguminous crop (Fabaceae) to diversify botanical families and support soil biological rotation."
            )
        else:
            benefits.append(
                f"Botanical family break between {f_fam} ({first_crop['name']}) and {s_fam} ({second_crop['name']}) interrupts host-specific pest and pathogen cycles."
            )

    if p_fam and f_fam and p_fam == f_fam:
        cautions.append(
            f"Season 1 ({first_crop['name']}) shares family {f_fam} with the field's previous crop ({previous_crop.get('name')})."
        )

    # 4. Rooting depth alternation (FAO-56 Table 22 max_rooting_depth_m)
    r1 = (first_traits or {}).get("max_rooting_depth_m")
    r2 = (second_traits or {}).get("max_rooting_depth_m")
    if r1 and r2:
        d1 = 0.5 * (float(r1["low"]) + float(r1["high"]))
        d2 = 0.5 * (float(r2["low"]) + float(r2["high"]))
        if abs(d1 - d2) >= 0.4:
            benefits.append(
                f"Alternates rooting depth profiles ({first_crop['name']}: ~{r1['low']:g}–{r1['high']:g} m vs. "
                f"{second_crop['name']}: ~{r2['low']:g}–{r2['high']:g} m), reducing uniform root-zone nutrient and moisture extraction."
            )

    # 5. Paddy-to-upland drainage transition check
    if first_crop["id"] == "rice" and second_crop["id"] != "rice":
        cautions.append(
            f"Transitioning from bunded/flooded rice to upland {second_crop['name']} requires field drainage and seedbed aeration between seasons."
        )

    if blockers:
        status = "blocked"
        summary = "Blocked by life-cycle or calendar overlap"
    elif f_fam and s_fam and f_fam == s_fam:
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
        "first_crop_id": first_crop["id"],
        "first_crop_name": first_crop["name"],
        "first_family": f_fam,
        "second_crop_id": second_crop["id"],
        "second_crop_name": second_crop["name"],
        "second_family": s_fam,
        "blockers": blockers,
        "cautions": cautions,
        "benefits": benefits,
        "scientific_disclaimer": (
            "Rotation checks evaluate botanical family alternation, life-cycle compatibility, window turnaround, "
            "and rooting depth references. Exact nitrogen fixation (kg/ha) or disease-suppression percentages "
            "are not fabricated without site-specific trial measurements."
        ),
    }


def plan_global_rotations(
    farm,
    dataset,
    *,
    candidate_crop_ids: list[str] | None = None,
    max_sequences: int = 16,
) -> list[dict]:
    """Generate constraint-based two-season crop rotation plans for any international location."""
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

    if candidate_crop_ids:
        pool = [cid for cid in candidate_crop_ids if cid in cards_s1 and cid in cards_s2]
    else:
        viable = [
            cid
            for cid, c in cards_s1.items()
            if c["status"] in {"possible", "check"} and cards_s2.get(cid, {}).get("status") in {"possible", "check"}
        ]
        pool = viable[:10] if len(viable) >= 4 else list(cards_s1)[:8]

    prev_identity = crop_by_id(farm.current) if farm.current not in (None, "unknown") else None
    identities = {cid: (crop_by_id(cid) or {"id": cid, "name": cards_s1[cid]["name"]}) for cid in pool}

    sequences = []
    for c1_id in pool:
        for c2_id in pool:
            c1 = identities[c1_id]
            c2 = identities[c2_id]
            s1_card = cards_s1[c1_id]
            s2_card = cards_s2[c2_id]

            trans = evaluate_transition(
                c1,
                c2,
                previous_crop=prev_identity,
                first_traits=traits_by_crop.get(c1_id),
                second_traits=traits_by_crop.get(c2_id),
                w1=w1,
                w2=w2,
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

            sequences.append(
                {
                    "id": f"{c1_id}_then_{c2_id}",
                    "name": f"{c1['name']} → {c2['name']}",
                    "overall_status": overall_status,
                    "summary": trans["summary"],
                    "season_1": {
                        "window": w1.label,
                        "crop_id": c1_id,
                        "crop_name": c1["name"],
                        "family": c1.get("family"),
                        "status": s1_card["status"],
                        "reason": s1_card["reason"],
                        "water": s1_card["water"],
                    },
                    "season_2": {
                        "window": w2.label,
                        "crop_id": c2_id,
                        "crop_name": c2["name"],
                        "family": c2.get("family"),
                        "status": s2_card["status"],
                        "reason": s2_card["reason"],
                        "water": s2_card["water"],
                    },
                    "transition": trans,
                }
            )

    order_map = {"complementary": 0, "conditional": 1, "caution": 2, "outside": 3, "blocked": 4}
    sequences.sort(key=lambda r: (order_map.get(r["overall_status"], 9), r["name"].casefold()))
    return sequences[:max_sequences]
