"""AgroShift 3D Earth & Live Monitoring Engine."""
from __future__ import annotations

from typing import Any

from .processors import (
    _pixel_at,
    compute_layer_update_frequencies,
    downscale_moisture_to_parcel_grid,
    extract_raster_pixel,
    fuse_inverse_variance,
    fuse_soil_wetness_3way,
    process_soil_3d_profile,
    process_soil_ph,
    process_terrain_grid,
    process_terrain_stencil,
    soil_context,
    soil_profile_wcs,
    terrain_context,
    terrain_grid_context,
)


def __getattr__(name: str) -> Any:
    if name == "build_3d_field_slab":
        from .engine_3d import build_3d_field_slab

        return build_3d_field_slab
    if name == "evaluate_live_rotation_state":
        from .live_monitor import evaluate_live_rotation_state

        return evaluate_live_rotation_state
    if name == "render_3d_monitor_png":
        from .render_3d import render_3d_monitor_png

        return render_3d_monitor_png
    raise AttributeError(f"module 'agroshift.monitoring' has no attribute '{name}'")


__all__ = [
    "_pixel_at",
    "build_3d_field_slab",
    "compute_layer_update_frequencies",
    "downscale_moisture_to_parcel_grid",
    "evaluate_live_rotation_state",
    "extract_raster_pixel",
    "fuse_inverse_variance",
    "fuse_soil_wetness_3way",
    "process_soil_3d_profile",
    "process_soil_ph",
    "process_terrain_grid",
    "process_terrain_stencil",
    "render_3d_monitor_png",
    "soil_context",
    "soil_profile_wcs",
    "terrain_context",
    "terrain_grid_context",
]
