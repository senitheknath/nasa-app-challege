"""3D Field Slab assembly combining Atmosphere, Canopy, 5x5 Terrain Mesh, and 4-Horizon Soil Profile."""
from __future__ import annotations

import math
from typing import Any

from agroshift.earth_data.satellite import fetch_satellite_overpasses
from agroshift.monitoring.processors import (
    compute_layer_update_frequencies,
    process_soil_3d_profile,
    process_terrain_grid,
    process_terrain_stencil,
)

try:
    from agroshift.monitoring.processors import (
        downscale_moisture_to_parcel_grid,
        fuse_soil_wetness_3way,
    )
except ImportError:
    def _fuse_inverse_variance_fallback(measurements: list[tuple[float, float]]) -> dict[str, float]:
        valid = [(float(v), float(s)) for v, s in measurements if s is not None and s > 0]
        if not valid:
            return {"fused_value": 0.0, "fused_sigma": 0.0, "min_input_sigma": 0.0, "variance_reduction_pct": 0.0}
        weights = [1.0 / (s * s) for _, s in valid]
        w_sum = sum(weights)
        val = sum(w * v for w, (v, _) in zip(weights, valid)) / w_sum
        sig = math.sqrt(1.0 / w_sum)
        min_sig = min(s for _, s in valid)
        var_red = (1.0 - (sig * sig) / (min_sig * min_sig)) * 100.0
        return {
            "fused_value": round(val, 2),
            "fused_sigma": round(sig, 2),
            "min_input_sigma": round(min_sig, 2),
            "variance_reduction_pct": round(var_red, 1),
        }

    def fuse_soil_wetness_3way(
        s1_sar_moisture_pct: float,
        s2_ndmi_moisture_pct: float | None,
        fao_smap_prior_pct: float,
        *,
        s1_sigma: float = 4.5,
        s2_sigma: float = 5.0,
        prior_sigma: float = 6.0,
    ) -> dict[str, Any]:
        meas = [(s1_sar_moisture_pct, s1_sigma), (fao_smap_prior_pct, prior_sigma)]
        if s2_ndmi_moisture_pct is not None:
            meas.append((s2_ndmi_moisture_pct, s2_sigma))
        return _fuse_inverse_variance_fallback(meas)

    def downscale_moisture_to_parcel_grid(
        coarse_moisture_pct: float,
        wetness_index_grid: list[float],
        twi_grid: list[float],
        *,
        kappa_w: float = 4.2,
        kappa_topo: float = 1.6,
    ) -> list[float]:
        n = len(wetness_index_grid)
        if n == 0:
            return []
        mean_w = sum(wetness_index_grid) / n
        mean_twi = sum(twi_grid) / n
        return [
            round(coarse_moisture_pct + kappa_w * (w - mean_w) + kappa_topo * (t - mean_twi), 2)
            for w, t in zip(wetness_index_grid, twi_grid)
        ]
from agroshift.science.climate.climate import compute_daily_agromet_indices
from agroshift.science.climate.power import coordinates
from agroshift.science.soil_water.soil_and_water import (
    classify_usda_soil_texture,
    compute_saxton_rawls_hydraulics,
    fetch_soil_profile,
)

_SOIL_HORIZONS: tuple[tuple[str, float, float, float, float], ...] = (
    # (label, top_m, bottom_m, clay_depth_factor, soc_depth_factor)
    ("0-5cm", 0.00, 0.05, 0.96, 1.15),
    ("5-15cm", 0.05, 0.15, 1.00, 1.00),
    ("15-30cm", 0.15, 0.30, 1.06, 0.72),
    ("30-100cm", 0.30, 1.00, 1.12, 0.42),
)


def _build_atmosphere_layer(latitude: float, dataset: Any) -> dict[str, Any]:
    """Extract rainfall, temperature, solar radiation, VPD, and ET0 from NASA POWER dataset or latitude prior."""
    if dataset is not None and hasattr(dataset, "frame") and not dataset.frame.empty:
        df = dataset.frame
        recent = df.tail(14).copy()
        recent.attrs["latitude"] = latitude
        indices = compute_daily_agromet_indices(recent)
        n_days = max(1, len(recent))
        rain_mm_day = round(float(recent["PRECTOTCORR"].mean()), 2) if "PRECTOTCORR" in recent else 0.0
        temp_c = round(float(recent["T2M"].mean()), 2) if "T2M" in recent else 25.0
        solar = indices.get("solar_mj_m2_day")
        solar_mj = round(float(solar), 2) if solar is not None and math.isfinite(solar) else 18.5
        vpd = indices.get("vpd_kpa")
        vpd_kpa = round(float(vpd), 3) if vpd is not None and math.isfinite(vpd) else 1.15
        et0_total = indices.get("et0_pm_mm") if math.isfinite(indices.get("et0_pm_mm") or float("nan")) else indices.get("et0_mm")
        et0_mm_day = round(float(et0_total) / n_days, 2) if et0_total is not None and math.isfinite(et0_total) else 4.2
        return {
            "rainfall_mm_day": rain_mm_day,
            "temperature_c": temp_c,
            "solar_radiation_mj_m2_day": solar_mj,
            "vpd_kpa": vpd_kpa,
            "et0_mm_day": et0_mm_day,
            "et0_method": indices.get("et0_method", "fao56"),
            "source": "NASA POWER agroclimatology",
        }

    abs_lat = abs(float(latitude))
    temp_prior = round(max(6.0, 28.5 - 0.35 * abs_lat), 1)
    rain_prior = round(max(1.2, 5.2 - 0.06 * abs_lat), 2)
    solar_prior = round(max(11.0, 21.5 - 0.14 * abs_lat), 1)
    vpd_prior = round(0.75 + 0.025 * max(0.0, temp_prior - 15.0), 2)
    et0_prior = round(max(2.0, 0.16 * temp_prior + 0.12 * solar_prior - 1.2), 2)
    return {
        "rainfall_mm_day": rain_prior,
        "temperature_c": temp_prior,
        "solar_radiation_mj_m2_day": solar_prior,
        "vpd_kpa": vpd_prior,
        "et0_mm_day": et0_prior,
        "et0_method": "latitude_climate_prior",
        "source": "Latitude agroclimatic prior (no POWER dataset supplied)",
    }


def _build_5x5_grid_coords(bbox_str: str) -> list[tuple[int, int, float, float]]:
    """Generate 25 (row, col, lat, lon) coordinates over a W,S,E,N bounding box."""
    west, south, east, north = [float(x) for x in bbox_str.split(",")]
    coords: list[tuple[int, int, float, float]] = []
    for row in range(5):
        y_frac = row / 4.0
        pt_lat = north - y_frac * (north - south)
        for col in range(5):
            x_frac = col / 4.0
            pt_lon = west + x_frac * (east - west)
            coords.append((row, col, round(pt_lat, 6), round(pt_lon, 6)))
    return coords


def _synthesize_5x5_elevations(
    center_lat: float,
    center_lon: float,
    base_elev_m: float,
    slope_pct: float,
    runoff_dx: float,
    runoff_dy: float,
    grid_coords: list[tuple[int, int, float, float]],
) -> list[float]:
    """Synthesize a deterministic 5x5 watershed/valley topography anchored to DEM elevation and runoff gradient."""
    # Seed phase angles deterministically from coordinates so each zone has distinct valley/ridge geometry
    seed = abs(math.sin(center_lat * 12.9898 + center_lon * 78.233)) * 43758.5453
    phase = (seed - math.floor(seed)) * math.pi * 2.0
    relief_amp = max(14.0, min(65.0, float(slope_pct) * 14.0 + 18.0))

    up_dx = -runoff_dx if (runoff_dx or runoff_dy) else 0.7071
    up_dy = -runoff_dy if (runoff_dx or runoff_dy) else 0.7071

    elevs: list[float] = []
    for row, col, _pt_lat, _pt_lon in grid_coords:
        # Normalized [-1, 1] coordinates across the catchment
        u = (col - 2.0) / 2.0
        v = (row - 2.0) / 2.0

        # Project onto primary drainage axis (along_valley) and cross-valley axis (across_valley)
        along = u * (-up_dx) + v * (-up_dy)
        across = u * (-up_dy) - v * (-up_dx)

        # Meandering valley channel centerline
        meander = 0.28 * math.sin(along * 2.2 + phase)
        dist_from_channel = abs(across - meander)

        # V-to-U shaped valley trough flanked by upland ridges + side tributary gullies
        valley_wall = (dist_from_channel ** 1.45) * relief_amp * 0.85
        longitudinal_slope = -along * relief_amp * 0.28
        side_ridges = 0.22 * relief_amp * math.cos(u * 2.6 + phase * 0.5) * math.sin(v * 2.4 - phase * 0.3)

        z = base_elev_m - 0.35 * relief_amp + valley_wall + longitudinal_slope + side_ridges
        elevs.append(round(z, 2))
    return elevs


def _build_terrain_3d_mesh(
    latitude: float,
    longitude: float,
    *,
    boundary: Any = None,
    area_ha: float | None = None,
    offline: bool = False,
) -> dict[str, Any]:
    """Construct a 5x5 structured 3D surface grid with runoff vectors and pooling risk."""
    from agroshift.earth_data.geometry import resolve_geometry

    geom = resolve_geometry("terrain_dem", latitude, longitude, boundary=boundary, area_ha=area_ha or 4.0)
    mesh_bbox_str = geom["bbox"]
    west, south, east, north = [float(x) for x in mesh_bbox_str.split(",")]

    boundary_uv: list[dict[str, Any]] = []
    if isinstance(boundary, dict) and boundary.get("type") == "Polygon":
        ring = (boundary.get("coordinates") or [[]])[0]
        if len(ring) >= 4:
            dx_span = max(1e-6, east - west)
            dy_span = max(1e-6, north - south)
            for pt in ring[:-1] if ring[0] == ring[-1] else ring:
                pt_lon, pt_lat = float(pt[0]), float(pt[1])
                boundary_uv.append(
                    {
                        "u": round((pt_lon - west) / dx_span, 4),
                        "v": round((north - pt_lat) / dy_span, 4),
                        "latitude": round(pt_lat, 6),
                        "longitude": round(pt_lon, 6),
                    }
                )

    grid_coords = _build_5x5_grid_coords(mesh_bbox_str)
    points = [(lat, lon) for _, _, lat, lon in grid_coords]

    stencil_res = process_terrain_stencil(latitude, longitude, offline=offline)
    stencil_val = stencil_res.get("value") if isinstance(stencil_res.get("value"), dict) else {}

    elevs: list[float] = []
    source_label = "Synthesized 5x5 micro-relief mesh anchored to regional prior"

    if not offline:
        grid_res = process_terrain_grid(points, offline=False)
        grid_val = grid_res.get("value") if isinstance(grid_res.get("value"), dict) else {}
        verts = grid_val.get("vertices") if isinstance(grid_val.get("vertices"), list) else []
        if len(verts) == 25:
            elevs = [float(v["elevation_m"]) for v in verts]
            stencil_val = grid_val
            source_label = "Copernicus DEM GLO-90 (5x5 sampled grid)"

    if len(elevs) != 25:
        base_elev = float(stencil_val.get("elevation_m") or round(85.0 + abs(latitude) * 3.5, 1))
        base_slope = float(stencil_val.get("regional_slope_pct") or 1.8)
        rv = stencil_val.get("runoff_vector") or {}
        rdx = float(rv.get("dx", -0.7071))
        rdy = float(rv.get("dy", -0.7071))
        elevs = _synthesize_5x5_elevations(latitude, longitude, base_elev, base_slope, rdx, rdy, grid_coords)
        if stencil_val.get("elevation_m") is not None:
            source_label = "Copernicus DEM GLO-90 stencil + synthesized 5x5 relief mesh"

    elev_grid = [[elevs[r * 5 + c] for c in range(5)] for r in range(5)]
    elev_min = min(elevs)
    elev_max = max(elevs)

    # west, south, east, north already resolved above (including optional polygon context padding)
    cell_dx_m = max(10.0, ((east - west) / 4.0) * 111320.0 * max(0.1, math.cos(math.radians(latitude))))
    cell_dy_m = max(10.0, ((north - south) / 4.0) * 111320.0)

    vertices: list[dict[str, Any]] = []
    for r in range(5):
        for c in range(5):
            idx = r * 5 + c
            _, _, pt_lat, pt_lon = grid_coords[idx]
            z = elev_grid[r][c]
            rel_h = round(z - elev_min, 2)

            c_left, c_right = max(0, c - 1), min(4, c + 1)
            r_up, r_down = max(0, r - 1), min(4, r + 1)
            dz_dx = (elev_grid[r][c_right] - elev_grid[r][c_left]) / ((c_right - c_left) * cell_dx_m)
            dz_dy = (elev_grid[r_up][c] - elev_grid[r_down][c]) / ((r_down - r_up) * cell_dy_m)
            grad_mag = math.hypot(dz_dx, dz_dy)
            slope_pct = round(grad_mag * 100.0, 2)
            flow_dx = round(-dz_dx / grad_mag, 4) if grad_mag > 1e-9 else 0.0
            flow_dy = round(-dz_dy / grad_mag, 4) if grad_mag > 1e-9 else 0.0

            elev_span = max(1.0, elev_max - elev_min)
            norm_h = rel_h / elev_span
            twi = round(math.log((100.0 + (1.0 - norm_h) * 450.0) / max(0.015, grad_mag)), 2)
            s1_s2_wetness_idx = round(max(0.1, min(0.95, 0.55 - 0.35 * norm_h)), 3)
            z_conditioned = round(z - 0.6 * s1_s2_wetness_idx, 2)

            if rel_h <= 0.22 * elev_span and slope_pct < 2.5:
                pooling_risk = "high"
            elif rel_h <= 0.40 * elev_span and slope_pct < 4.5:
                pooling_risk = "moderate"
            else:
                pooling_risk = "low"

            vertices.append(
                {
                    "row": r,
                    "col": c,
                    "x_norm": round(c / 4.0, 2),
                    "y_norm": round(r / 4.0, 2),
                    "latitude": pt_lat,
                    "longitude": pt_lon,
                    "elevation_m": z_conditioned,
                    "relative_height_m": rel_h,
                    "slope_pct": slope_pct,
                    "flow_dx": flow_dx,
                    "flow_dy": flow_dy,
                    "pooling_risk": pooling_risk,
                    "twi": twi,
                    "s1_s2_wetness_idx": s1_s2_wetness_idx,
                }
            )

    center_v = vertices[12]
    runoff_vector = stencil_val.get("runoff_vector") or {
        "dx": center_v["flow_dx"],
        "dy": center_v["flow_dy"],
        "gradient_pct": center_v["slope_pct"],
    }
    mean_slope = round(sum(v["slope_pct"] for v in vertices) / len(vertices), 2)
    span_km_x = round((cell_dx_m * 4.0) / 1000.0, 2)
    span_km_y = round((cell_dy_m * 4.0) / 1000.0, 2)
    area_km2 = round(span_km_x * span_km_y, 2)
    return {
        "grid_size": 5,
        "span_km_x": span_km_x,
        "span_km_y": span_km_y,
        "area_km2": area_km2,
        "elevation_m": round(sum(elevs) / len(elevs), 1),
        "elevation_min_m": round(elev_min, 1),
        "elevation_max_m": round(elev_max, 1),
        "regional_slope_pct": stencil_val.get("regional_slope_pct", mean_slope),
        "concavity_m": stencil_val.get("concavity_m", 0.0),
        "suggested_drainage_prior": stencil_val.get("suggested_drainage_prior", "well_drained"),
        "runoff_vector": runoff_vector,
        "boundary_uv": boundary_uv,
        "vertices": vertices,
        "dem_tier": "Copernicus DEM GLO-30 (30m) + 10m S1/S2 Drainage Conditioning",
        "source": source_label,
    }


def _build_soil_3d_horizons(
    latitude: float,
    longitude: float,
    *,
    active_root_depth_m: float,
    drainage_prior: str,
    rainfall_mm_day: float,
    offline: bool,
) -> list[dict[str, Any]]:
    """Build 4 vertical soil horizons combining SoilGrids properties, Saxton-Rawls hydraulics, and root presence."""
    wcs = process_soil_3d_profile(
        latitude,
        longitude,
        properties=("phh2o", "clay", "sand", "silt", "soc"),
        depths=("0-5cm", "5-15cm", "15-30cm"),
        quantiles=("mean",),
        offline=offline,
    )
    wcs_layers = wcs.get("layers_by_depth", {}) if wcs.get("status") == "verified" else {}
    rest_profile = fetch_soil_profile(latitude, longitude, allow_network=not offline)

    base_ph = float(rest_profile.get("ph_median") or 6.2)
    base_sand = float(rest_profile.get("sand_pct") or 46.0)
    base_clay = float(rest_profile.get("clay_pct") or 26.0)
    base_soc = float(rest_profile.get("soc_g_kg") or 12.0)

    wetness_frac = min(0.92, max(0.28, 0.42 + 0.04 * rainfall_mm_day + (0.18 if drainage_prior == "waterlogged" else 0.0)))

    horizons: list[dict[str, Any]] = []
    for idx, (label, top_m, bottom_m, clay_fac, soc_fac) in enumerate(_SOIL_HORIZONS):
        layer_wcs = wcs_layers.get(label, {})
        ph_val = layer_wcs.get("phh2o", {}).get("mean")
        clay_val = layer_wcs.get("clay", {}).get("mean")
        sand_val = layer_wcs.get("sand", {}).get("mean")
        silt_val = layer_wcs.get("silt", {}).get("mean")
        soc_val = layer_wcs.get("soc", {}).get("mean")

        clay_pct = round(float(clay_val) if clay_val is not None else min(65.0, base_clay * clay_fac), 1)
        sand_pct = round(float(sand_val) if sand_val is not None else max(8.0, base_sand * (2.0 - clay_fac)), 1)
        silt_pct = round(float(silt_val) if silt_val is not None else max(5.0, 100.0 - clay_pct - sand_pct), 1)
        soc_g_kg = round(float(soc_val) if soc_val is not None else max(2.5, base_soc * soc_fac), 1)
        ph = round(float(ph_val) if ph_val is not None else min(8.5, max(4.2, base_ph + 0.08 * idx)), 2)

        hydraulics = compute_saxton_rawls_hydraulics(sand_pct, clay_pct, soc_g_kg)
        wp = hydraulics["wilting_point_vol_pct"]
        fc = hydraulics["field_capacity_vol_pct"]
        depth_wetness = min(0.98, wetness_frac + 0.04 * idx)
        vol_moisture = round(wp + depth_wetness * (fc - wp), 1)

        horizons.append(
            {
                "depth_label": label,
                "depth_top_m": top_m,
                "depth_bottom_m": bottom_m,
                "ph": ph,
                "sand_pct": sand_pct,
                "clay_pct": clay_pct,
                "silt_pct": silt_pct,
                "soc_g_kg": soc_g_kg,
                "usda_texture": classify_usda_soil_texture(sand_pct, silt_pct, clay_pct),
                "hydraulics": hydraulics,
                "volumetric_moisture_pct": vol_moisture,
                "roots_present": bool(float(active_root_depth_m) >= top_m),
            }
        )
    return horizons


def build_3d_field_slab(
    latitude: float,
    longitude: float,
    country: str = "LK",
    *,
    boundary: Any = None,
    area_ha: float | None = None,
    dataset: Any = None,
    active_root_depth_m: float = 0.45,
    ndvi_current: float = 0.58,
    offline: bool = False,
) -> dict[str, Any]:
    """Assemble a complete 3D Field Slab (atmosphere, canopy, 5x5 terrain mesh, 4 soil horizons, update frequencies)."""
    from agroshift.earth_data.geometry import normalize_boundary, resolve_geometry

    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    norm_boundary = normalize_boundary(boundary)
    geom = resolve_geometry("terrain_dem", lat, lon, boundary=norm_boundary, area_ha=area_ha or 4.0)

    atmosphere_layer = _build_atmosphere_layer(lat, dataset)
    overpasses = fetch_satellite_overpasses(
        lat,
        lon,
        boundary=norm_boundary,
        area_ha=area_ha,
        offline=offline,
    )
    is_bare_soil = float(ndvi_current) < 0.20

    # Estimate ECOSTRESS canopy-air thermal stress delta (deg C) from VPD & vegetation cover
    thermal_stress_delta = round(
        max(0.2, 0.8 + 1.3 * float(atmosphere_layer["vpd_kpa"]) - 1.1 * max(0.0, float(ndvi_current))),
        2,
    )
    canopy_layer = {
        "ndvi_current": round(float(ndvi_current), 3),
        "is_bare_soil": is_bare_soil,
        "ecostress_thermal_stress_delta_c": thermal_stress_delta,
        "overpasses": overpasses,
    }

    terrain_3d_mesh = _build_terrain_3d_mesh(
        lat,
        lon,
        boundary=norm_boundary,
        area_ha=area_ha,
        offline=offline,
    )

    soil_3d_horizons = _build_soil_3d_horizons(
        lat,
        lon,
        active_root_depth_m=active_root_depth_m,
        drainage_prior=terrain_3d_mesh["suggested_drainage_prior"],
        rainfall_mm_day=atmosphere_layer["rainfall_mm_day"],
        offline=offline,
    )

    clouds = [a["cloud_cover_pct"] for a in overpasses.get("acquisitions", []) if a.get("cloud_cover_pct") is not None]
    avg_cloud = sum(clouds) / len(clouds) if clouds else 22.0
    update_frequencies = compute_layer_update_frequencies(
        cloud_cover_pct=avg_cloud,
        is_bare_soil=is_bare_soil,
    )

    verts = terrain_3d_mesh["vertices"]
    wetness_grid = [float(v["s1_s2_wetness_idx"]) for v in verts]
    twi_grid = [float(v["twi"]) for v in verts]
    mean_wet_idx = sum(wetness_grid) / max(1, len(wetness_grid))

    fao_smap_prior_pct = float(soil_3d_horizons[0]["volumetric_moisture_pct"])
    s1_sar_moisture_pct = round(max(5.0, min(55.0, fao_smap_prior_pct + (mean_wet_idx - 0.38) * 8.0)), 2)
    s2_ndmi_moisture_pct = (
        round(max(5.0, min(55.0, fao_smap_prior_pct + (float(ndvi_current) - 0.5) * 4.0)), 2)
        if avg_cloud < 85.0
        else None
    )
    moisture_fusion_3way = fuse_soil_wetness_3way(
        s1_sar_moisture_pct,
        s2_ndmi_moisture_pct,
        fao_smap_prior_pct,
    )

    downscaled_grid = downscale_moisture_to_parcel_grid(
        float(moisture_fusion_3way["fused_value"]),
        wetness_grid,
        twi_grid,
    )
    for v, dm in zip(verts, downscaled_grid):
        v["downscaled_moisture_pct"] = dm
    parcel_mean_moisture_conserved_pct = round(sum(downscaled_grid) / max(1, len(downscaled_grid)), 2)

    combined_parcel_dt_days = update_frequencies.get("combined_parcel_dt_days")
    if combined_parcel_dt_days is None:
        clear_frac = 1.0 - min(95.0, max(0.0, float(avg_cloud))) / 100.0
        combined_parcel_dt_days = round(1.0 / (clear_frac * ((1.0 / 5.0) + (1.0 / 8.0)) + (1.0 / 6.0)), 2)

    sensor_fusion = {
        "stack": [
            "SENTINEL2_L2A (10m)",
            "SENTINEL1_GRD (10m SAR)",
            "LANDSAT_8_9 (30m/100m)",
            "COP_DEM_GLO30 (30m)",
            "ECOSTRESS (70m)",
            "SOILGRIDS_250M",
            "NASA_POWER_SMAP_GPM",
        ],
        "moisture_fusion_3way": moisture_fusion_3way,
        "combined_parcel_dt_days": combined_parcel_dt_days,
        "parcel_mean_moisture_conserved_pct": parcel_mean_moisture_conserved_pct,
    }

    return {
        "location": {
            "country": str(country).upper(),
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "area_ha": area_ha,
            "bounding_box": geom["bbox"],
        },
        "active_root_depth_m": round(float(active_root_depth_m), 2),
        "offline": bool(offline),
        "atmosphere_layer": atmosphere_layer,
        "canopy_layer": canopy_layer,
        "terrain_3d_mesh": terrain_3d_mesh,
        "soil_3d_horizons": soil_3d_horizons,
        "update_frequencies": update_frequencies,
        "sensor_fusion": sensor_fusion,
    }
