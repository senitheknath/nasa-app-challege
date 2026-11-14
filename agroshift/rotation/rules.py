"""Agronomic transition rules for evaluating crop sequences."""
from __future__ import annotations

from typing import Any, Callable

from .contracts import CropProfile, RotationConfig, RuleFinding

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


def window_overlap_days(w1: Any, w2: Any) -> int:
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


def rule_lifecycle(
    first: CropProfile,
    second: CropProfile,
    _prev: CropProfile | None,
    _w1: Any,
    _w2: Any,
    _cfg: RotationConfig,
) -> list[RuleFinding]:
    """Flag annual vs perennial life-cycle conflicts."""
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
    """Verify non-overlapping seasonal calendars leaving time for harvest and land prep."""
    if w1 is None or w2 is None:
        return []
    overlap = window_overlap_days(w1, w2)
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
    """Evaluate botanical family alternation and legume diversification benefits."""
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
    """Evaluate vertical root-zone nutrient and moisture extraction alternation."""
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
    """Flag transitions from flooded wetland/paddy to waterlogging-sensitive upland crops."""
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
