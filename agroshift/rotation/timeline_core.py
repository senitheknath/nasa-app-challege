"""Domain-agnostic mathematical interval & state-space DAG scheduling core.

Implements classical time-expanded DAG trajectory optimization without domain
bias (zero agricultural terminology in this core module). Operates strictly on
discrete intervals, phase partitions, turnaround buffers, and delay slack.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class ActivityNode:
    """Mathematical activity with duration bounds, start interval, and phase fractions."""

    id: str
    earliest_start: int
    latest_start: int
    duration_min: int
    duration_nominal: int
    duration_max: int
    phase_fractions: tuple[float, ...] = (0.2, 0.3, 0.3, 0.2)
    base_utility: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)

    def phase_intervals(self, start_t: int, duration: int) -> list[tuple[int, int]]:
        """Partition activity duration into discrete phase intervals [p_start, p_end]."""
        intervals: list[tuple[int, int]] = []
        curr = start_t
        n_phases = len(self.phase_fractions)
        for i, frac in enumerate(self.phase_fractions):
            if i == n_phases - 1:
                p_end = start_t + duration
            else:
                p_len = max(1, int(round(duration * frac)))
                p_end = min(start_t + duration, curr + p_len)
            intervals.append((curr, p_end))
            curr = p_end
        return intervals


@dataclass(frozen=True)
class ArcConstraint:
    """Pairwise transition constraint between consecutive activities."""

    min_buffer: int = 7
    optimal_buffer: int = 21
    max_idle_buffer: int = 60
    compatibility_score: float = 0.0
    hard_blocked: bool = False
    status: str = "compatible"
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScheduledSlot:
    """Exact placement of an activity on the timeline with buffer and delay slack."""

    activity_id: str
    start_t: int
    end_t_min: int
    end_t_nominal: int
    end_t_max: int
    phase_intervals: list[tuple[int, int]]
    turnaround_buffer_after: int
    delay_slack: int
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Trajectory:
    """Multi-activity schedule sequence with exact timeline and composite score."""

    slots: tuple[ScheduledSlot, ...]
    total_score: float
    feasible: bool
    status: str
    reasons: tuple[str, ...] = ()

    @property
    def activity_ids(self) -> tuple[str, ...]:
        return tuple(s.activity_id for s in self.slots)


# ArcEvaluator signature: (prev_activity, next_activity) -> ArcConstraint
ArcEvaluator = Callable[[ActivityNode, ActivityNode], ArcConstraint]


def solve_trajectories(
    candidate_stages: Sequence[Sequence[ActivityNode]],
    arc_evaluator: ArcEvaluator,
    *,
    max_trajectories: int = 16,
) -> list[Trajectory]:
    """Solve multi-stage activity trajectories using forward DAG path enumeration.

    Calculates exact nominal/min/max completion times, phase intervals, turnaround
    buffers, and maximum delay slack for each trajectory.
    """
    if not candidate_stages or any(len(stage) == 0 for stage in candidate_stages):
        return []

    if len(candidate_stages) == 1:
        # Trivial single-stage
        trajectories: list[Trajectory] = []
        for a in candidate_stages[0]:
            start = a.earliest_start
            phases = a.phase_intervals(start, a.duration_nominal)
            slot = ScheduledSlot(
                activity_id=a.id,
                start_t=start,
                end_t_min=start + a.duration_min,
                end_t_nominal=start + a.duration_nominal,
                end_t_max=start + a.duration_max,
                phase_intervals=phases,
                turnaround_buffer_after=0,
                delay_slack=a.latest_start - a.earliest_start,
                payload=a.payload,
            )
            trajectories.append(
                Trajectory(
                    slots=(slot,),
                    total_score=a.base_utility,
                    feasible=True,
                    status="feasible",
                )
            )
        trajectories.sort(key=lambda t: t.total_score, reverse=True)
        return trajectories[:max_trajectories]

    # Two-stage or multi-stage forward DAG construction
    # We solve pairwise stages sequentially
    paths: list[list[ActivityNode]] = [[a] for a in candidate_stages[0]]
    for stage_idx in range(1, len(candidate_stages)):
        next_candidates = candidate_stages[stage_idx]
        new_paths: list[list[ActivityNode]] = []
        for p in paths:
            last = p[-1]
            for nxt in next_candidates:
                new_paths.append(p + [nxt])
        paths = new_paths

    evaluated_trajectories: list[Trajectory] = []

    for path in paths:
        slots: list[ScheduledSlot] = []
        curr_t = path[0].earliest_start
        path_score = path[0].base_utility
        is_feasible = True
        overall_status = "complementary"
        all_reasons: list[str] = []

        for i in range(len(path) - 1):
            act = path[i]
            nxt = path[i + 1]

            # Nominal start and end
            start_i = max(act.earliest_start, curr_t)
            end_nominal_i = start_i + act.duration_nominal
            end_min_i = start_i + act.duration_min
            end_max_i = start_i + act.duration_max
            phases_i = act.phase_intervals(start_i, act.duration_nominal)

            arc = arc_evaluator(act, nxt)
            path_score += nxt.base_utility + arc.compatibility_score
            all_reasons.extend(arc.reasons)

            # Check next start
            nxt_start = max(nxt.earliest_start, end_nominal_i + arc.min_buffer)
            buffer_after = nxt_start - end_nominal_i

            # Check hard collision or infeasibility
            if arc.hard_blocked or buffer_after < arc.min_buffer:
                is_feasible = False
                overall_status = "blocked"
            elif buffer_after < arc.optimal_buffer:
                if overall_status != "blocked":
                    overall_status = "caution"
            elif arc.status in {"caution", "conditional"}:
                if overall_status != "blocked":
                    overall_status = arc.status

            # Calculate slack: how much act start can slip before violating nxt_start
            max_act_start = nxt.latest_start - arc.min_buffer - act.duration_nominal
            delay_slack = max(0, max_act_start - start_i)

            slots.append(
                ScheduledSlot(
                    activity_id=act.id,
                    start_t=start_i,
                    end_t_min=end_min_i,
                    end_t_nominal=end_nominal_i,
                    end_t_max=end_max_i,
                    phase_intervals=phases_i,
                    turnaround_buffer_after=buffer_after,
                    delay_slack=delay_slack,
                    payload=act.payload,
                )
            )
            curr_t = nxt_start

        # Append final activity slot
        final_act = path[-1]
        final_start = curr_t
        final_nominal = final_start + final_act.duration_nominal
        final_min = final_start + final_act.duration_min
        final_max = final_start + final_act.duration_max
        final_phases = final_act.phase_intervals(final_start, final_act.duration_nominal)
        final_slack = max(0, final_act.latest_start - final_start)

        slots.append(
            ScheduledSlot(
                activity_id=final_act.id,
                start_t=final_start,
                end_t_min=final_min,
                end_t_nominal=final_nominal,
                end_t_max=final_max,
                phase_intervals=final_phases,
                turnaround_buffer_after=0,
                delay_slack=final_slack,
                payload=final_act.payload,
            )
        )

        evaluated_trajectories.append(
            Trajectory(
                slots=tuple(slots),
                total_score=round(path_score, 2),
                feasible=is_feasible,
                status=overall_status,
                reasons=tuple(all_reasons),
            )
        )

    # Sort: feasible first, complementary first, then highest score
    status_order = {"complementary": 0, "conditional": 1, "caution": 2, "outside": 3, "blocked": 4}
    evaluated_trajectories.sort(
        key=lambda t: (
            0 if t.feasible else 1,
            status_order.get(t.status, 9),
            -t.total_score,
        )
    )

    return evaluated_trajectories[:max_trajectories]
