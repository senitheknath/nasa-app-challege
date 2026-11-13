"""Data contracts and configuration for the crop rotation engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

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
