"""Physical satellite, raster, soil, and terrain processing primitives."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import math
from typing import Any

from PIL import Image

from agroshift.earth_data.provider_http import reference
from agroshift.science.climate.power import DataError, coordinates

SOIL = "https://maps.isric.org/mapserv"


def _missing(source: str, kind: str, detail: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source": source,
        "kind": kind,
        "detail": detail,
        "value": None,
        "access": None,
        "retrieved_at": None,
    }


def extract_raster_pixel(image: Image.Image, lat: float, lon: float) -> Any:
    """Sample a single pixel from a WGS84 GeoTIFF image using its affine tiepoint/scale tags."""
    tags = image.tag_v2
    keys = tags.get(34735, ())
    if (2048, 0, 1, 4326) not in [tuple(keys[i : i + 4]) for i in range(4, len(keys), 4)]:
        raise ValueError("Raster does not identify WGS84")
    scale_x, scale_y, _ = tags[33550]
    i, j, _, x, y, _ = tags[33922]
    if not (scale_x > 0 and scale_y > 0):
        raise ValueError("Unknown raster transform")
    col = math.floor(i + (lon - x) / scale_x)
    row = math.floor(j + (y - lat) / scale_y)
    if not (0 <= col < image.width and 0 <= row < image.height):
        raise ValueError("Point outside returned raster")
    return image.getpixel((col, row))


_pixel_at = extract_raster_pixel


def process_soil_ph(
    latitude: float,
    longitude: float,
    *,
    offline: bool = False,
    record: bool = False,
) -> dict[str, Any]:
    """Retrieve ISRIC SoilGrids 2.0 modelled mean topsoil pH (0-5 cm, H2O) via WCS."""
    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    detail = "ISRIC SoilGrids 2.0 modelled mean pH in water, 0–5 cm depth, 250 m source grid."
    kind = "modelled"
    if abs(lat) > 89.995 or abs(lon) > 179.995:
        return _missing(SOIL, kind, "No soil sample at this map edge.")
    crs = "http://www.opengis.net/def/crs/EPSG/0/4326"
    params = {
        "map": "/map/phh2o.map",
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "COVERAGEID": "phh2o_0-5cm_mean",
        "FORMAT": "GEOTIFF_INT16",
        "SCALESIZE": "x(5),y(5)",
        "SUBSETTINGCRS": crs,
        "OUTPUTCRS": crs,
        "SUBSET": [f"X({lon-.005:.7f},{lon+.005:.7f})", f"Y({lat-.005:.7f},{lat+.005:.7f})"],
    }

    def parse(body: bytes) -> float:
        with Image.open(BytesIO(body)) as grid:
            if grid.format != "TIFF" or grid.size != (5, 5):
                raise ValueError("Unexpected SoilGrids raster size")
            raw = extract_raster_pixel(grid, lat, lon)
            if not isinstance(raw, int) or not 0 < raw <= 140 or str(raw) == str(grid.tag_v2.get(42113)):
                raise DataError("No usable SoilGrids pH estimate at this location.")
            return raw / 10

    return reference(
        SOIL,
        params,
        parse,
        kind=kind,
        detail=detail,
        offline=offline,
        record=record,
        source="https://docs.isric.org/globaldata/soilgrids/WCS_from_Python.html",
    )


soil_context = process_soil_ph


def process_soil_3d_profile(
    latitude: float,
    longitude: float,
    *,
    properties: tuple[str, ...] = ("phh2o", "clay", "sand", "silt", "soc", "bdod", "cec", "cfvo", "wv0033", "wv1500"),
    depths: tuple[str, ...] = ("0-5cm", "5-15cm", "15-30cm"),
    quantiles: tuple[str, ...] = ("mean", "Q0.05", "Q0.95"),
    offline: bool = False,
    record: bool = False,
) -> dict[str, Any]:
    """Retrieve multi-property, multi-depth ISRIC SoilGrids 2.0 WCS layers with uncertainty and pedological interpretation."""
    from agroshift.science.soil_water.soil import SOILGRIDS_DEPTHS, SOILGRIDS_PROPERTIES, interpret_soil_profile, normalize_soilgrids_value

    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    if abs(lat) > 89.995 or abs(lon) > 179.995:
        return _missing(SOIL, "modelled", "No soil sample at this map edge.")

    crs = "http://www.opengis.net/def/crs/EPSG/0/4326"
    layers_by_depth: dict[str, dict] = {d: {} for d in depths if d in SOILGRIDS_DEPTHS}
    provenance_cells = []
    any_verified = False
    retrieved_at = None

    tasks: list[tuple[str, str, str, str, dict[str, Any]]] = []
    for prop in properties:
        if prop not in SOILGRIDS_PROPERTIES:
            continue
        for depth in depths:
            if depth not in SOILGRIDS_DEPTHS:
                continue
            for q in quantiles:
                cov_id = f"{prop}_{depth}_{q}"
                params = {
                    "map": f"/map/{prop}.map",
                    "SERVICE": "WCS",
                    "VERSION": "2.0.1",
                    "REQUEST": "GetCoverage",
                    "COVERAGEID": cov_id,
                    "FORMAT": "GEOTIFF_INT16",
                    "SCALESIZE": "x(5),y(5)",
                    "SUBSETTINGCRS": crs,
                    "OUTPUTCRS": crs,
                    "SUBSET": [f"X({lon-.005:.7f},{lon+.005:.7f})", f"Y({lat-.005:.7f},{lat+.005:.7f})"],
                }
                tasks.append((prop, depth, q, cov_id, params))

    def _fetch_one(task: tuple[str, str, str, str, dict[str, Any]]) -> dict[str, Any]:
        p_name, _depth, _q, cov_id, params = task

        def _parse_cell(body: bytes) -> dict[str, Any]:
            with Image.open(BytesIO(body)) as grid:
                if grid.format != "TIFF" or grid.size != (5, 5):
                    raise ValueError("Unexpected SoilGrids raster size")
                raw = extract_raster_pixel(grid, lat, lon)
                if not isinstance(raw, int) or str(raw) == str(grid.tag_v2.get(42113)):
                    raise DataError(f"No usable SoilGrids {p_name} estimate at this location.")
                norm = normalize_soilgrids_value(p_name, raw)
                if not norm["valid"]:
                    raise DataError(f"Out-of-range SoilGrids {p_name} estimate.")
                return norm

        return reference(
            SOIL,
            params,
            _parse_cell,
            kind="modelled",
            detail=f"ISRIC SoilGrids 2.0 {cov_id} (250 m source grid).",
            offline=offline,
            record=record,
            source="https://docs.isric.org/globaldata/soilgrids/WCS_from_Python.html",
        )

    if tasks:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_fetch_one, tasks))
    else:
        results = []

    for (prop, depth, q, cov_id, _params), res in zip(tasks, results):
        if res["status"] == "verified" and isinstance(res["value"], dict):
            any_verified = True
            retrieved_at = retrieved_at or res["retrieved_at"]
            q_entry = layers_by_depth[depth].setdefault(prop, {})
            q_entry[q] = res["value"]["normalized_value"]
            if q == "mean":
                q_entry["raw_mean"] = res["value"]["raw_value"]
                q_entry["original_unit"] = res["value"]["original_unit"]
                q_entry["normalized_unit"] = res["value"]["normalized_unit"]
                q_entry["conversion_method"] = res["value"]["conversion_method"]
            provenance_cells.append(
                {
                    "coverage_id": cov_id,
                    "access": res["access"],
                    "retrieved_at": res["retrieved_at"],
                    **res["value"],
                }
            )

    # Fallback to top-5cm pH archive if only phh2o_0-5cm_mean is archived offline
    if not any_verified:
        top_ph = process_soil_ph(lat, lon, offline=offline, record=False)
        if top_ph["status"] == "verified" and top_ph["value"] is not None:
            any_verified = True
            retrieved_at = top_ph["retrieved_at"]
            raw_equiv = int(round(float(top_ph["value"]) * 10))
            norm = normalize_soilgrids_value("phh2o", raw_equiv)
            layers_by_depth.setdefault("0-5cm", {})["phh2o"] = {
                "mean": norm["normalized_value"],
                "raw_mean": norm["raw_value"],
                "original_unit": norm["original_unit"],
                "normalized_unit": norm["normalized_unit"],
                "conversion_method": norm["conversion_method"],
            }

    if not any_verified:
        return _missing(SOIL, "modelled", "No verified SoilGrids profile layers available for this request.")

    interpretation = interpret_soil_profile(layers_by_depth)
    ph_top = layers_by_depth.get("0-5cm", {}).get("phh2o", {})
    return {
        "status": "verified",
        "kind": "modelled",
        "data_category": "modelled_estimate",
        "source": "https://docs.isric.org/globaldata/soilgrids/WCS_from_Python.html",
        "retrieved_at": retrieved_at,
        "access": provenance_cells[0]["access"] if provenance_cells else "archive",
        "value": interpretation["topsoil_0_30cm"].get("ph_h2o") or ph_top.get("mean"),
        "q05": ph_top.get("Q0.05"),
        "q95": ph_top.get("Q0.95"),
        "layers_by_depth": layers_by_depth,
        "topsoil_0_30cm": interpretation["topsoil_0_30cm"],
        "provenance_cells": provenance_cells,
        "scientific_safeguards": interpretation["scientific_safeguards"],
        "detail": "ISRIC SoilGrids 2.0 multi-depth WCS profile (~250 m grid). Modelled estimate, not a field soil test.",
    }


soil_profile_wcs = process_soil_3d_profile


def process_terrain_stencil(
    latitude: float,
    longitude: float,
    *,
    offline: bool = False,
    record: bool = False,
) -> dict[str, Any]:
    """Retrieve Copernicus DEM GLO-90 (90 m) elevation, local terrain slope, and downhill runoff vector."""
    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    url = "https://api.open-meteo.com/v1/elevation"
    d = 0.00081  # ~90 m spacing
    params = {
        "latitude": f"{lat:.5f},{lat+d:.5f},{lat-d:.5f},{lat:.5f},{lat:.5f}",
        "longitude": f"{lon:.5f},{lon:.5f},{lon:.5f},{lon+d:.5f},{lon-d:.5f}",
    }

    def _parse(body: bytes) -> dict[str, Any]:
        elevs = json.loads(body.decode("utf-8")).get("elevation", [])
        if not isinstance(elevs, list) or len(elevs) < 5:
            raise ValueError("Incomplete DEM response")
        c, n, s, e, w = [float(x) for x in elevs[:5]]
        dy_m = 2.0 * d * 111320.0
        dx_m = max(10.0, 2.0 * d * 111320.0 * math.cos(math.radians(lat)))
        dz_dy = (n - s) / dy_m
        dz_dx = (e - w) / dx_m
        grad_mag = math.hypot(dz_dx, dz_dy)
        slope_pct = round(grad_mag * 100.0, 2)
        if grad_mag > 1e-9:
            flow_dx = round(-dz_dx / grad_mag, 4)
            flow_dy = round(-dz_dy / grad_mag, 4)
        else:
            flow_dx = 0.0
            flow_dy = 0.0
        min_nbr = min(n, s, e, w)
        mean_nbr = (n + s + e + w) / 4.0
        local_relief_m = round(max(0.0, c - min_nbr), 2)
        concavity_m = round(c - mean_nbr, 2)
        low_lying = local_relief_m <= 1.2 and slope_pct < 1.5 and concavity_m <= 0.3
        drain_prior = "waterlogged" if low_lying else "well_drained"
        return {
            "elevation_m": round(c, 1),
            "regional_slope_pct": slope_pct,
            "local_relief_m": local_relief_m,
            "concavity_m": concavity_m,
            "runoff_vector": {
                "dx": flow_dx,
                "dy": flow_dy,
                "gradient_pct": slope_pct,
            },
            "suggested_drainage_prior": drain_prior,
            "why_we_think_this": (
                f"Copernicus DEM shows {c:.0f} m elevation with {slope_pct:.1f}% slope and "
                f"{local_relief_m:.1f} m height above nearest local drainage ("
                + ("low-lying basin — check for waterlogging" if low_lying else "sheds surface water — likely well-drained")
                + ")."
            ),
            "dem_resolution_m": 90,
            "slope_class": (
                "flat_to_gentle (<2%)"
                if slope_pct < 2.0
                else ("moderate (2-8%)" if slope_pct < 8.0 else "steep (>=8%)")
            ),
            "scale_disclaimer": "Derived from 90 m Copernicus DEM; does not capture field-level terracing, bunds, or micro-topography.",
        }

    return reference(
        url,
        params,
        _parse,
        kind="digital_elevation_model",
        detail="Copernicus DEM GLO-90 (~90 m) elevation, slope, and local drainage relief estimate.",
        offline=offline,
        record=record,
    )


terrain_context = process_terrain_stencil


def process_terrain_grid(
    points: list[tuple[float, float]],
    *,
    offline: bool = False,
    record: bool = False,
) -> dict[str, Any]:
    """Batch-sample Copernicus DEM GLO-90 elevation across interior polygon points in one HTTP call."""
    if not points:
        raise ValueError("At least one coordinate point is required.")
    if len(points) == 1:
        return process_terrain_stencil(points[0][0], points[0][1], offline=offline, record=record)
    center_lat, center_lon = points[0]
    center_res = process_terrain_stencil(center_lat, center_lon, offline=offline, record=record)
    url = "https://api.open-meteo.com/v1/elevation"
    params = {
        "latitude": ",".join(f"{p[0]:.5f}" for p in points),
        "longitude": ",".join(f"{p[1]:.5f}" for p in points),
    }

    def _parse(body: bytes) -> dict[str, Any]:
        elevs = [float(x) for x in json.loads(body.decode("utf-8")).get("elevation", [])]
        center_val = center_res.get("value") if isinstance(center_res.get("value"), dict) else {}
        if not elevs:
            return center_val
        elev_min = min(elevs)
        elev_max = max(elevs)
        vertices = [
            {
                "latitude": round(float(pt_lat), 6),
                "longitude": round(float(pt_lon), 6),
                "elevation_m": round(float(elev), 2),
                "relative_height_m": round(float(elev) - elev_min, 2),
            }
            for (pt_lat, pt_lon), elev in zip(points, elevs)
        ]
        merged = dict(center_val)
        merged["elevation_m"] = round(sum(elevs) / len(elevs), 1)
        merged["elevation_min_m"] = round(elev_min, 1)
        merged["elevation_max_m"] = round(elev_max, 1)
        merged["elevation_range_m"] = round(elev_max - elev_min, 1)
        merged["sample_points"] = len(elevs)
        merged["vertices"] = vertices
        return merged

    grid_res = reference(
        url,
        params,
        _parse,
        kind="digital_elevation_model",
        detail=f"Copernicus DEM GLO-90 (~90 m) multi-point polygon sample ({len(points)} interior points).",
        offline=offline,
        record=record,
    )
    grid_val = grid_res.get("value") if isinstance(grid_res.get("value"), dict) else {}
    return grid_res if grid_val.get("elevation_min_m") is not None else center_res


terrain_grid_context = process_terrain_grid


def compute_layer_update_frequencies(
    cloud_cover_pct: float = 22.0,
    is_bare_soil: bool = False,
) -> dict[str, Any]:
    """Compute cloud-adjusted optical revisit intervals and multi-sensor calibration frequencies."""
    clamped_cloud = min(95.0, max(0.0, float(cloud_cover_pct)))
    p_cloud = clamped_cloud / 100.0
    clear_fraction = 1.0 - p_cloud

    hls_t_orbit = 2.5
    ecostress_t_orbit = 4.0
    smap_t_orbit = 1.5
    s2_t_orbit = 5.0
    l89_t_orbit = 8.0
    s1_t_orbit = 6.0

    hls_dt_clean = round(hls_t_orbit / clear_fraction, 2)
    ecostress_dt_clean = round(ecostress_t_orbit / clear_fraction, 2)
    s2_dt_clean = round(s2_t_orbit / clear_fraction, 2)
    l89_dt_clean = round(l89_t_orbit / clear_fraction, 2)
    combined_canopy_dt = round(1.0 / ((1.0 / hls_dt_clean) + (1.0 / ecostress_dt_clean)), 2)

    parcel_rate = clear_fraction * ((1.0 / s2_t_orbit) + (1.0 / l89_t_orbit)) + (1.0 / s1_t_orbit)
    combined_parcel_dt = round(1.0 / parcel_rate, 2)

    return {
        "cloud_cover_pct": round(clamped_cloud, 1),
        "p_cloud": round(p_cloud, 4),
        "is_bare_soil": bool(is_bare_soil),
        "combined_canopy_dt_days": combined_canopy_dt,
        "combined_parcel_dt_days": combined_parcel_dt,
        "layers": {
            "hlsl30": {
                "sensor": "HLSL30",
                "resolution_m": 30,
                "t_orbit_days": hls_t_orbit,
                "dt_clean_days": hls_dt_clean,
                "cloud_piercing": False,
                "role": "surface_reflectance_ndvi",
            },
            "ecostress": {
                "sensor": "ECOSTRESS",
                "resolution_m": 70,
                "t_orbit_days": ecostress_t_orbit,
                "dt_clean_days": ecostress_dt_clean,
                "cloud_piercing": False,
                "role": "canopy_water_stress",
            },
            "smap_lband": {
                "sensor": "SMAP L-band",
                "resolution_m": 9000,
                "t_orbit_days": smap_t_orbit,
                "dt_clean_days": smap_t_orbit,
                "cloud_piercing": True,
                "role": "root_zone_wetness",
            },
            "copernicus_dem": {
                "sensor": "Copernicus DEM",
                "resolution_m": 90,
                "t_orbit_days": None,
                "dt_clean_days": None,
                "cadence": "static",
                "cloud_piercing": True,
                "role": "terrain_elevation_slope",
            },
            "fao56_root_zone": {
                "sensor": "FAO-56 Water Balance",
                "resolution_m": None,
                "dt_tick_hours": 24.0,
                "dt_clean_days": 1.0,
                "cadence": "24h",
                "cloud_piercing": True,
                "role": "daily_root_zone_model",
            },
            "bare_soil_swir_ph": {
                "sensor": "SoilGrids / Bare-Soil SWIR pH",
                "resolution_m": 30,
                "active": bool(is_bare_soil),
                "ndvi_threshold": 0.20,
                "t_orbit_days": hls_t_orbit,
                "dt_clean_days": hls_dt_clean if is_bare_soil else None,
                "cadence": "active_bare_soil_window" if is_bare_soil else "dormant_canopy_closed",
                "role": "bare_soil_ph_calibration",
            },
            "sentinel2_l2a": {
                "sensor": "Sentinel-2 L2A",
                "resolution_m": 10,
                "t_orbit_days": s2_t_orbit,
                "dt_clean_days": s2_dt_clean,
                "cloud_piercing": False,
                "role": "parcel_optical_ndvi_swir",
            },
            "landsat_8_9": {
                "sensor": "Landsat 8/9 C2 L2",
                "resolution_m": 30,
                "t_orbit_days": l89_t_orbit,
                "dt_clean_days": l89_dt_clean,
                "cloud_piercing": False,
                "role": "parcel_optical_and_thermal",
            },
            "sentinel1_sar": {
                "sensor": "Sentinel-1 C-Band SAR",
                "resolution_m": 10,
                "t_orbit_days": s1_t_orbit,
                "dt_clean_days": s1_t_orbit,
                "cloud_piercing": True,
                "role": "cloud_piercing_parcel_wetness",
            },
            "copernicus_dem_glo30": {
                "sensor": "Copernicus DEM GLO-30",
                "resolution_m": 30,
                "t_orbit_days": None,
                "dt_clean_days": "static",
                "cloud_piercing": True,
                "role": "terrain_3d_mesh_30m",
            },
        },
    }


class ProgressiveFusionAccumulator:
    """Recursive inverse-variance MVUE accumulator tracking step-by-step uncertainty reduction."""

    def __init__(self) -> None:
        self._precision_sum: float = 0.0
        self._weighted_sum: float = 0.0
        self._min_input_sigma: float = float("inf")
        self._sources: list[str] = []
        self._convergence_steps: list[dict[str, Any]] = []

    def update(self, source_name: str, value: float, sigma: float) -> dict[str, Any]:
        """Incorporate a newly arrived sensor estimate and record its convergence snapshot."""
        val_f = float(value)
        sig_f = float(sigma)
        if not math.isfinite(val_f):
            raise ValueError(f"Measurement value must be finite, got {value}.")
        if not math.isfinite(sig_f) or sig_f <= 0.0:
            raise ValueError(f"Measurement sigma must be positive, got {sigma}.")

        w = 1.0 / (sig_f * sig_f)
        self._precision_sum += w
        self._weighted_sum += w * val_f
        if sig_f < self._min_input_sigma:
            self._min_input_sigma = sig_f
        self._sources.append(str(source_name))

        fused_val = self._weighted_sum / self._precision_sum
        fused_var = 1.0 / self._precision_sum
        fused_sig = math.sqrt(fused_var)
        var_red = (1.0 - fused_var / (self._min_input_sigma * self._min_input_sigma)) * 100.0

        snapshot = {
            "step": len(self._convergence_steps) + 1,
            "source": str(source_name),
            "input_value": round(val_f, 2),
            "input_sigma": round(sig_f, 2),
            "fused_value": round(fused_val, 2),
            "fused_sigma": round(fused_sig, 2),
            "variance_reduction_pct": round(var_red, 1),
        }
        self._convergence_steps.append(snapshot)
        return dict(snapshot)

    @property
    def sensor_count(self) -> int:
        return len(self._convergence_steps)

    @property
    def sources_used(self) -> list[str]:
        return list(self._sources)

    @property
    def convergence_steps(self) -> list[dict[str, Any]]:
        return [dict(step) for step in self._convergence_steps]

    def result(self) -> dict[str, Any]:
        """Return the current MVUE summary and full convergence trace."""
        if not self._convergence_steps:
            raise ValueError("At least one (source_name, value, sigma) measurement is required.")
        fused_val = self._weighted_sum / self._precision_sum
        fused_var = 1.0 / self._precision_sum
        fused_sig = math.sqrt(fused_var)
        var_red = (1.0 - fused_var / (self._min_input_sigma * self._min_input_sigma)) * 100.0
        return {
            "fused_value": round(fused_val, 2),
            "fused_sigma": round(fused_sig, 2),
            "min_input_sigma": round(self._min_input_sigma, 2),
            "variance_reduction_pct": round(var_red, 1),
            "sensor_count": len(self._convergence_steps),
            "sources_used": list(self._sources),
            "convergence_steps": [dict(step) for step in self._convergence_steps],
        }


def fuse_progressive_steps(steps: list[tuple[str, float, float]]) -> dict[str, Any]:
    """Run sequential inverse-variance MVUE updates over (source_name, value, sigma) steps."""
    if not steps:
        raise ValueError("At least one (source_name, value, sigma) step is required.")
    acc = ProgressiveFusionAccumulator()
    for source_name, value, sigma in steps:
        acc.update(source_name, value, sigma)
    return acc.result()


def fuse_inverse_variance(measurements: list[tuple[float, float]]) -> dict[str, float]:
    """Combine independent (value, sigma) sensor estimates via inverse-variance MVUE weighting."""
    if not measurements:
        raise ValueError("At least one (value, sigma) measurement is required.")
    acc = ProgressiveFusionAccumulator()
    for idx, (val, sig) in enumerate(measurements, start=1):
        acc.update(f"sensor_{idx}", val, sig)
    res = acc.result()
    return {
        "fused_value": res["fused_value"],
        "fused_sigma": res["fused_sigma"],
        "min_input_sigma": res["min_input_sigma"],
        "variance_reduction_pct": res["variance_reduction_pct"],
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
    """Progressively fuse FAO-56/SMAP prior (9km), Sentinel-1 SAR (10m), and optional Sentinel-2 NDMI (20m)."""
    steps: list[tuple[str, float, float]] = [
        ("fao56_smap_prior", float(fao_smap_prior_pct), float(prior_sigma)),
        ("sentinel1_sar", float(s1_sar_moisture_pct), float(s1_sigma)),
    ]
    if s2_ndmi_moisture_pct is not None:
        steps.append(("sentinel2_ndmi", float(s2_ndmi_moisture_pct), float(s2_sigma)))

    fused = fuse_progressive_steps(steps)
    return {
        **fused,
        "fused_moisture_pct": fused["fused_value"],
    }


def downscale_moisture_to_parcel_grid(
    coarse_moisture_pct: float,
    wetness_index_grid: list[float],
    twi_grid: list[float],
    *,
    kappa_w: float = 4.2,
    kappa_topo: float = 1.6,
) -> list[float]:
    """Mass-conserving topographic-spectral spatial downscaling from coarse prior to 10 m parcel grid."""
    if len(wetness_index_grid) != len(twi_grid):
        raise ValueError("wetness_index_grid and twi_grid must have the same length.")
    n = len(wetness_index_grid)
    if n == 0:
        return []
    mean_w = sum(wetness_index_grid) / n
    mean_twi = sum(twi_grid) / n
    return [
        round(
            float(coarse_moisture_pct)
            + float(kappa_w) * (float(w_i) - mean_w)
            + float(kappa_topo) * (float(twi_i) - mean_twi),
            2,
        )
        for w_i, twi_i in zip(wetness_index_grid, twi_grid)
    ]
