"""Crop rotation and multi-season sequence planning package."""
from __future__ import annotations

from .contracts import CropProfile, RotationConfig, RuleFinding, Severity, TransitionStatus
from .engine import evaluate_transition, plan_global_rotations, select_candidate_pool
from .rules import (
    DEFAULT_RULES,
    TransitionRule,
    rule_drainage_transition,
    rule_family_succession,
    rule_lifecycle,
    rule_rooting_depth,
    rule_window_turnaround,
    window_overlap_days,
)

__all__ = [
    "DEFAULT_RULES",
    "CropProfile",
    "RotationConfig",
    "RuleFinding",
    "Severity",
    "TransitionStatus",
    "TransitionRule",
    "evaluate_transition",
    "plan_global_rotations",
    "rule_drainage_transition",
    "rule_family_succession",
    "rule_lifecycle",
    "rule_rooting_depth",
    "rule_window_turnaround",
    "select_candidate_pool",
    "window_overlap_days",
]
