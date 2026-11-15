"""Modular Starlette JSON API exposing AgroShift scientific, earth-data, and rotation engines."""
from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware

from api.routes import all_routes

app = Starlette(
    debug=False,
    routes=all_routes,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
