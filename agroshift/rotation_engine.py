"""Modular, constraint-based international crop rotation and multi-season sequence planner."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from itertools import product
from typing import Any, Callable, Literal, Sequence

from .knowledge import crop_by_id, global_traits
from .screening import find_options

Severity = Literal["blocker", "caution", "benefit"]
TransitionStatus = Literal["blocked", "caution", "conditional", "complementary"]


@dataclass(frozen=True)
class CropProfile:
    """Normalized crop profile with reviewed global traits and taxonomy."""

    id: str
    name: str
    family: str | None = None
    group_name: str | None = None
    life_cycle: str = "annual"
    traits: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_crop_and_traits(
        cls,
        crop: dict[str, Any],
        traits: dict[str, dict[str, Any]] | None = None,
    ) -> "CropProfile":
        return cls(
            id=str(crop.get("id", "")),
            name=str(crop.get("name", "")),
            family=crop.get("family"),
            group_name=crop.get("group_name"),
            life_cycle=crop.get("life_cycle") or "annual",
            traits=dict(traits or {}),
        )

    def trait_value(self, name: str) -> Any:
        rec = self.traits.get(name)
        if not rec:
            return None
        if "value" in rec and rec["value"] is not None:
            return rec["value"]
        if "low" in rec and "high" in rec:
            return (float(rec["low"]), float(rec["high"]))
        return None


@dataclass(frozen=True)
class RotationConfig:
    """Configurable agronomic thresholds without hardcoded domain literals."""

    min_rooting_delta_m: float = 0.4
    min_turnaround_days: int = 0
    nitrogen_fixing_families: frozenset[str] = frozenset({"Fabaceae"})
    max_candidate_pool: int = 10
    max_sequences: int = 16


@dataclass(frozen=True)
class RuleFinding:
    rule_id: str
    severity: Severity
    message: str


# Rule signature: (first, second, previous, w1, w2, config) -> list[RuleFinding]
TransitionRule = Callable[
    [
        CropProfile,
        CropProfile,
        CropProfile | None,
        Any,
        Any,
        RotationConfig,
    ],
    list[RuleFinding],
]


def _window_overlap_days(w1: Any, w2: Any) -> int:
    """Check whether two recurring seasonal windows overlap within an annual cycle."""
    if w1 is None or w2 is None:
        return 0
    s1, e1 = w1.dates(2023)
    s2, e2 = w2.dates(2023)
    if s2 < s1:
        s2, e2 = w2.dates(2024)
    overlap_start = max(s1, s2)
    overlap_end = min(e1, e2)
    return max(0, (overlap_end - overlap_start).days + 1)


# ---------------------------------------------------------------------------
# Modular Transition Rules
# ---------------------------------------------------------------------------


def rule_lifecycle(
    first: CropProfile,
    second: CropProfile,
    _prev: CropProfile | None,
    _w1: Any,
    _w2: Any,
    _cfg: RotationConfig,
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    if first.life_cycle == "perennial":
        findings.append(
            RuleFinding(
                "lifecycle_perennial_s1",
                "blocker",
                f"{first.name} is a perennial crop and occupies the field across multiple seasons; "
                f"it cannot be rotated into {second.name} within a single annual two-season cycle.",
            )
        )
    if second.life_cycle == "perennial":
        findings.append(
            RuleFinding(
                "lifecycle_perennial_s2",
                "caution",
                f"{second.name} is a perennial crop; planting it in Season 2 commits the field beyond the current year.",
            )
        )
    return findings


def rule_window_turnaround(
    _first: CropProfile,
    _second: CropProfile,
    _prev: CropProfile | None,
    w1: Any,
    w2: Any,
    _cfg: RotationConfig,
) -> list[RuleFinding]:
    if w1 is None or w2 is None:
        return []
    overlap = _window_overlap_days(w1, w2)
    if overlap > 0:
        return [
            RuleFinding(
                "window_overlap",
                "blocker",
                f"Season 1 ({w1.label}) and Season 2 ({w2.label}) overlap by {overlap} days, "
                "leaving no turnaround time for harvest and land preparation.",
            )
        ]
    return []


def rule_family_succession(
    first: CropProfile,
    second: CropProfile,
    prev: CropProfile | None,
    _w1: Any,
    _w2: Any,
    cfg: RotationConfig,
) -> list[RuleFinding]:
    findings: list[RuleFinding] = []
    f_fam = first.family
    s_fam = second.family
    p_fam = prev.family if prev else None

    if f_fam and s_fam:
        if f_fam == s_fam:
            findings.append(
                RuleFinding(
                    "same_family_s1_s2",
                    "caution",
                    f"Both Season 1 ({first.name}) and Season 2 ({second.name}) belong to {f_fam}; "
                    "consecutive same-family planting increases host-specific pest, disease, and weed carryover.",
                )
            )
        elif bool({f_fam, s_fam} & cfg.nitrogen_fixing_families):
            findings.append(
                RuleFinding(
                    "legume_diversification",
                    "benefit",
                    f"Alternates {f_fam} ({first.name}) with {s_fam} ({second.name}), "
                    "including a leguminous crop (Fabaceae) to diversify botanical families and support soil biological rotation.",
                )
            )
        else:
            findings.append(
                RuleFinding(
                    "family_break",
                    "benefit",
                    f"Botanical family break between {f_fam} ({first.name}) and {s_fam} ({second.name}) "
                    "interrupts host-specific pest and pathogen cycles.",
                )
            )

    if p_fam and f_fam and p_fam == f_fam:
        findings.append(
            RuleFinding(
                "same_family_prev_s1",
                "caution",
                f"Season 1 ({first.name}) shares family {f_fam} with the field's previous crop ({prev.name}).",
            )
        )
    return findings


def rule_rooting_depth(
    first: CropProfile,
    second: CropProfile,
    _prev: CropProfile | None,
    _w1: Any,
    _w2: Any,
    cfg: RotationConfig,
) -> list[RuleFinding]:
    r1 = first.trait_value("max_rooting_depth_m")
    r2 = second.trait_value("max_rooting_depth_m")
    if not (isinstance(r1, tuple) and isinstance(r2, tuple)):
        return []
    d1 = 0.5 * (r1[0] + r1[1])
    d2 = 0.5 * (r2[0] + r2[1])
    if abs(d1 - d2) >= cfg.min_rooting_delta_m:
        return [
            RuleFinding(
                "rooting_depth_alternation",
                "benefit",
                f"Alternates rooting depth profiles ({first.name}: ~{r1[0]:g}–{r1[1]:g} m vs. "
                f"{second.name}: ~{r2[0]:g}–{r2[1]:g} m), reducing uniform root-zone nutrient and moisture extraction.",
            )
        ]
    return []


def rule_drainage_transition(
    first: CropProfile,
    second: CropProfile,
    _prev: CropProfile | None,
    _w1: Any,
    _w2: Any,
    _cfg: RotationConfig,
) -> list[RuleFinding]:
    # Check if first crop is flooded/paddy and second crop is upland
    first_conflict = first.trait_value("persistent_waterlogging_conflict")
    second_conflict = second.trait_value("persistent_waterlogging_conflict")
    is_paddy_to_upland = (
        (first_conflict is False and second_conflict is True)
        or (first.id == "rice" and second.id != "rice")
    )
    if is_paddy_to_upland:
        return [
            RuleFinding(
                "drainage_transition",
                "caution",
                f"Transitioning from bunded/flooded {first.name} to upland {second.name} "
                "requires field drainage and seedbed aeration between seasons.",
            )
        ]
    return []


DEFAULT_RULES: tuple[TransitionRule, ...] = (
    rule_lifecycle,
    rule_window_turnaround,
    rule_family_succession,
    rule_rooting_depth,
    rule_drainage_transition,
)


# ---------------------------------------------------------------------------
# Public Engine API
# ---------------------------------------------------------------------------


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
) -> dict[str, Any]:
    """Evaluate botanical family, life-cycle, rooting-depth, and drainage transitions between consecutive crops."""
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
    """Generate constraint-based two-season crop rotation plans for any international location."""
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

            trans = evaluate_transition(
                p1,
                p2,
                previous_crop=prev_profile,
                w1=w1,
                w2=w2,
                config=config,
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
                }
            )

    order_map = {"complementary": 0, "conditional": 1, "caution": 2, "outside": 3, "blocked": 4}
    sequences.sort(key=lambda r: (order_map.get(r["overall_status"], 9), r["name"].casefold()))
    return sequences[:max_sequences]
