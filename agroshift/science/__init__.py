"""Core Agricultural Science Engine Package for AgroShift.

Organized into four cohesive scientific domains:
1. climate: NASA POWER observations, agro-meteorological aggregation, extremes radar.
2. soil_water: SoilGrids profiles, FAO-56 4-stage water balance, AquaCrop prototype.
3. knowledge: Reviewed FAO traits, crop catalogue, growth stages, pest records.
4. decision: Interval-valued MCDA decision engine, first-season screening, evidence combination.
"""
from __future__ import annotations

from . import climate, decision, knowledge, soil_water

__all__ = [
    "climate",
    "decision",
    "knowledge",
    "soil_water",
]
