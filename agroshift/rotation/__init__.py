"""Crop rotation and multi-season sequence planning package."""
from __future__ import annotations

from .engine import (
    DEFAULT_RULES,
    CropProfile,
    RotationConfig,
    RuleFinding,
    TransitionRule,
    evaluate_transition,
    plan_global_rotations,
    rule_drainage_transition,
    rule_family_succession,
    rule_lifecycle,
    rule_rooting_depth,
    rule_window_turnaround,
    select_candidate_pool,
)

__all__ = [
    "DEFAULT_RULES",
    "CropProfile",
    "RotationConfig",
    "RuleFinding",
    "TransitionRule",
    "evaluate_transition",
    "plan_global_rotations",
    "rule_drainage_transition",
    "rule_family_succession",
    "rule_lifecycle",
    "rule_rooting_depth",
    "rule_window_turnaround",
    "select_candidate_pool",
]
