"""AgroShift Core Agricultural Platform.

Modular architecture:
- agroshift.earth_data: Satellite imagery, spatial cache, field auto-fill, geospatial providers.
- agroshift.identity: User accounts, authentication, saved multi-farm persistence, boundaries.
- agroshift.rotation: Modular crop rotation engine, contracts, and decoupled agronomic rules.
- agroshift.science: Pure scientific engines grouped into climate, soil_water, knowledge, and decision.
"""
from __future__ import annotations

from importlib import import_module
import sys

# Forward-compatibility subpackage exports
from . import earth_data, identity, rotation, science

# Transparent alias map for legacy import compatibility
_LEGACY_MODULE_MAP = {
    "power": "agroshift.science.climate.power",
    "climate": "agroshift.science.climate.climate",
    "climate_insights": "agroshift.science.climate.climate_insights",
    "extremes": "agroshift.science.climate.extremes",
    "soil": "agroshift.science.soil_water.soil",
    "soil_and_water": "agroshift.science.soil_water.soil_and_water",
    "water_balance": "agroshift.science.soil_water.water_balance",
    "aquacrop_prototype": "agroshift.science.soil_water.aquacrop_prototype",
    "knowledge": "agroshift.science.knowledge.knowledge",
    "knowledge_store": "agroshift.science.knowledge.knowledge_store",
    "refresh_manager": "agroshift.science.knowledge.refresh_manager",
    "pests": "agroshift.science.knowledge.pests",
    "decision": "agroshift.science.decision.decision",
    "screening": "agroshift.science.decision.screening",
    "evidence_combination": "agroshift.science.decision.evidence_combination",
    "finder_report": "agroshift.science.decision.finder_report",
    "reporting": "agroshift.science.decision.reporting",
    "geography": "agroshift.earth_data.geography",
    "locations": "agroshift.earth_data.locations",
    "farm_context": "agroshift.earth_data.farm_context",
    "providers": "agroshift.earth_data.providers",
    "provider_http": "agroshift.earth_data.provider_http",
    "farm_records": "agroshift.identity.farm_records",
    "private_store": "agroshift.identity.private_store",
    "rotation_engine": "agroshift.rotation.engine",
    "auth_store": "agroshift.identity.auth",
    "geo_cache": "agroshift.earth_data.cache",
    "satellite_monitor": "agroshift.earth_data.satellite",
    "field_autofill": "agroshift.earth_data.autofill",
}


def __getattr__(name: str):
    if name in _LEGACY_MODULE_MAP:
        mod = import_module(_LEGACY_MODULE_MAP[name])
        sys.modules[f"agroshift.{name}"] = mod
        return mod
    raise AttributeError(f"module 'agroshift' has no attribute '{name}'")


# Pre-register aliases into sys.modules
for _alias, _target in _LEGACY_MODULE_MAP.items():
    _full_alias = f"agroshift.{_alias}"
    if _full_alias not in sys.modules:
        try:
            sys.modules[_full_alias] = import_module(_target)
        except Exception:
            pass

__all__ = [
    "earth_data",
    "identity",
    "rotation",
    "science",
]
