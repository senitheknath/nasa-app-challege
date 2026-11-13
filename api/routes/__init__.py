"""Modular route aggregation for AgroShift API."""
from __future__ import annotations

from api.routes.agronomy import routes as agronomy_routes
from api.routes.earth_data import routes as earth_data_routes
from api.routes.identity import routes as identity_routes
from api.routes.knowledge import routes as knowledge_routes
from api.routes.system import routes as system_routes

all_routes = [
    *system_routes,
    *earth_data_routes,
    *agronomy_routes,
    *knowledge_routes,
    *identity_routes,
]

__all__ = ["all_routes"]
