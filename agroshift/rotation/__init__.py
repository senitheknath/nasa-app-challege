"""Crop rotation and multi-season sequence planning package."""
from __future__ import annotations

from .contracts import (
    CropProfile,
    EnvironmentContext,
    RotationConfig,
    RuleFinding,
    Severity,
    TransitionStatus,
)
from .engine import evaluate_transition, plan_global_rotations, select_candidate_pool
from .rules import (
    DEFAULT_RULES,
    TransitionRule,
    rule_drainage_transition,
    rule_family_succession,
    rule_lifecycle,
    rule_nutrient_balance,
    rule_pathogen_carryover,
    rule_rooting_depth,
    rule_water_deficit_carryover,
    rule_window_turnaround,
    window_overlap_days,
)
from .timeline_adapter import build_physical_timeline, quantize_crop_to_activity
from .timeline_core import (
    ActivityNode,
    ArcConstraint,
    ScheduledSlot,
    Trajectory,
    solve_trajectories,
)

__all__ = [
    "ActivityNode",
    "ArcConstraint",
    "CropProfile",
    "DEFAULT_RULES",
    "EnvironmentContext",
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
    "rule_nutrient_balance",
    "rule_pathogen_carryover",
    "rule_rooting_depth",
    "rule_water_deficit_carryover",
    "rule_window_turnaround",
    "select_candidate_pool",
    "window_overlap_days",
    "ScheduledSlot",
    "Trajectory",
    "build_physical_timeline",
    "quantize_crop_to_activity",
    "solve_trajectories",
]
