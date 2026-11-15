"""Data contracts and configuration for the crop rotation engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["blocker", "caution", "benefit"]
TransitionStatus = Literal["blocked", "caution", "conditional", "complementary"]


@dataclass(frozen=True)
class EnvironmentContext:
    """Pre-processed physical and climatological field conditions."""

    drainage: str = "unknown"
    soil_texture: str = "unknown"
    soil_ph: float | None = None
    slope_pct: float | None = None
    irrigation: str = "unknown"
    rainfall_s1_mm: float | None = None
    water_need_s1_mm: float | None = None
    water_need_s2_mm: float | None = None


@dataclass(frozen=True)
class CropProfile:
    """Normalized crop profile with pre-digested scientific metrics and taxonomy."""

    id: str
    name: str
    family: str | None = None
    group_name: str | None = None
    life_cycle: str = "annual"
    traits: dict[str, dict[str, Any]] = field(default_factory=dict)
    kc_max: float | None = None
    waterlogging_sensitive: bool = False
    pests: frozenset[str] = field(default_factory=frozenset)
    is_nitrogen_fixer: bool = False
    nutrient_demand: str = "moderate"

    @classmethod
    def from_crop_and_traits(
        cls,
        crop: dict[str, Any],
        traits: dict[str, dict[str, Any]] | None = None,
        *,
        growth_stages: list[dict[str, Any]] | None = None,
        pest_records: list[dict[str, Any]] | None = None,
    ) -> "CropProfile":
        tr = dict(traits or {})
        fam = crop.get("family")
        is_fixer = (
            fam == "Fabaceae"
            or tr.get("nitrogen_fixing", {}).get("value") is True
            or crop.get("group_name") in {"Legumes", "Pulses"}
        )

        if is_fixer:
            demand = "fixer"
        elif fam in {"Poaceae", "Solanaceae"}:
            demand = "heavy"
        else:
            demand = "moderate"

        kc_max_val: float | None = None
        wl_sensitive = False
        if growth_stages:
            kc_vals = [s["kc_max"] for s in growth_stages if s.get("kc_max") is not None]
            if kc_vals:
                kc_max_val = max(kc_vals)
            wl_sensitive = any(s.get("waterlogging_sensitive") in (1, True) for s in growth_stages)

        conflict = tr.get("persistent_waterlogging_conflict")
        if conflict and (conflict.get("value") is True or conflict.get("value_text") == "true"):
            wl_sensitive = True

        pest_names: set[str] = set()
        if pest_records:
            for p in pest_records:
                if p.get("agent_name"):
                    pest_names.add(str(p["agent_name"]))

        return cls(
            id=str(crop.get("id", "")),
            name=str(crop.get("name", "")),
            family=fam,
            group_name=crop.get("group_name"),
            life_cycle=crop.get("life_cycle") or "annual",
            traits=tr,
            kc_max=kc_max_val,
            waterlogging_sensitive=wl_sensitive,
            pests=frozenset(pest_names),
            is_nitrogen_fixer=is_fixer,
            nutrient_demand=demand,
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
    heavy_feeding_families: frozenset[str] = frozenset({"Poaceae", "Solanaceae"})
    max_candidate_pool: int = 10
    max_sequences: int = 16


@dataclass(frozen=True)
class RuleFinding:
    rule_id: str
    severity: Severity
    message: str
