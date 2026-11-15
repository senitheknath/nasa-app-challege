#!/usr/bin/env python3
"""AgroShift 3D Field Slab & Live t > 0 Rotation Monitor CLI Demo.

Supports --random (diverse global agricultural polygons), --preset, custom
--lat/--lon/--country, --t-now, --ndvi, and --offline.
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agroshift.earth_data.autofill import derive_field_autofill
from agroshift.locations import load_history
from agroshift.monitoring import build_3d_field_slab, evaluate_live_rotation_state, render_3d_monitor_png
from agroshift.rotation import plan_global_rotations
from agroshift.science.climate.power import archived_history, request_parameters
from agroshift.science.decision.decision import Farm, Window


GLOBAL_ZONES: dict[str, dict] = {
    "anuradhapura": {
        "name": "Anuradhapura Cascade Tank Valley, Sri Lanka",
        "country": "LK",
        "lat": 8.3114,
        "lon": 80.4037,
        "windows": (Window(10, 1, 1, 20), Window(3, 1, 6, 30)),
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[80.372, 8.279], [80.436, 8.279], [80.436, 8.343], [80.372, 8.343], [80.372, 8.279]]],
        },
    },
    "nairobi": {
        "name": "Great Rift Valley Escarpment & Basin, Kenya",
        "country": "KE",
        "lat": -1.2921,
        "lon": 36.8219,
        "windows": (Window(3, 1, 6, 30), Window(10, 1, 1, 20)),
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[36.790, -1.324], [36.854, -1.324], [36.854, -1.260], [36.790, -1.260], [36.790, -1.324]]],
        },
    },
    "ames": {
        "name": "Des Moines Lobe Glacial Valley, Iowa, USA",
        "country": "US",
        "lat": 42.0308,
        "lon": -93.6319,
        "windows": (Window(4, 15, 7, 31), Window(8, 1, 11, 15)),
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[-93.664, 41.999], [-93.600, 41.999], [-93.600, 42.063], [-93.664, 42.063], [-93.664, 41.999]]],
        },
    },
    "punjab": {
        "name": "Sutlej River Alluvial Terrace & Basin, Punjab, India",
        "country": "IN",
        "lat": 30.9010,
        "lon": 75.8573,
        "windows": (Window(6, 15, 10, 15), Window(11, 1, 3, 20)),
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[75.825, 30.869], [75.889, 30.869], [75.889, 30.933], [75.825, 30.933], [75.825, 30.869]]],
        },
    },
    "mato_grosso": {
        "name": "Teles Pires River Valley & Cerrado Uplands, Brazil",
        "country": "BR",
        "lat": -12.5425,
        "lon": -55.7211,
        "windows": (Window(9, 15, 1, 15), Window(2, 1, 6, 15)),
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[-55.753, -12.574], [-55.689, -12.574], [-55.689, -12.510], [-55.753, -12.510], [-55.753, -12.574]]],
        },
    },
    "mekong": {
        "name": "Hau River Floodplain & Dyke Basin, Mekong Delta, Vietnam",
        "country": "VN",
        "lat": 10.0452,
        "lon": 105.7469,
        "windows": (Window(11, 15, 3, 1), Window(4, 1, 7, 30)),
        "polygon": {
            "type": "Polygon",
            "coordinates": [[[105.715, 10.013], [105.779, 10.013], [105.779, 10.077], [105.715, 10.077], [105.715, 10.013]]],
        },
    },
}


def _heat_glyph(rel_h: float, max_h: float) -> str:
    blocks = " .:-=+*#%@"
    if max_h <= 0:
        return "="
    idx = int(round(max(0.0, min(1.0, rel_h / max_h)) * (len(blocks) - 1)))
    return blocks[idx]


def _print_terrain_mesh(mesh: dict) -> None:
    print("\n[A] 3D TERRAIN MESH (5x5 DEM) & RUNOFF VECTOR")
    rv = mesh.get("runoff_vector") or {}
    print(
        f"  • Elevation : {mesh.get('elevation_m')} m "
        f"(min {mesh.get('elevation_min_m')} m, max {mesh.get('elevation_max_m')} m)"
    )
    print(
        f"  • Slope     : {mesh.get('regional_slope_pct')}% | "
        f"Concavity: {mesh.get('concavity_m')} m | "
        f"Drainage Prior: {mesh.get('suggested_drainage_prior')}"
    )
    print(
        f"  • Runoff Vec: dx={rv.get('dx')}, dy={rv.get('dy')} "
        f"(gradient {rv.get('gradient_pct')}%) | Source: {mesh.get('source')}"
    )

    verts = mesh.get("vertices") or []
    if len(verts) == 25:
        max_rel = max((v.get("relative_height_m", 0.0) for v in verts), default=1.0)
        grid = [[None] * 5 for _ in range(5)]
        for v in verts:
            grid[v["row"]][v["col"]] = v

        print("  • 5x5 Elevation Heatmap (m [glyph], P=pooling risk):")
        for r in range(5):
            cells = []
            for c in range(5):
                v = grid[r][c]
                g = _heat_glyph(v["relative_height_m"], max_rel)
                pool = "*" if v.get("pooling_risk") in ("high", "moderate") else " "
                cells.append(f"{v['elevation_m']:6.2f}[{g}{pool}]")
            print("    " + "  ".join(cells))


def _print_soil_horizons(horizons: list[dict], active_root_depth_m: float) -> None:
    print(f"\n[B] 4 VERTICAL 3D SOIL HORIZONS (Active Root Depth @ t_now: {active_root_depth_m:.2f} m)")
    print(
        f"  {'Depth':<9} {'pH':>5} {'Clay/Sand':>10} {'FC/WP %':>11} {'Moist %':>8} {'Texture':<14} {'Roots'}"
    )
    print("  " + "-" * 74)
    for h in horizons:
        hyd = h.get("hydraulics") or {}
        cs = f"{h.get('clay_pct', 0):.0f}/{h.get('sand_pct', 0):.0f}%"
        fc_wp = f"{hyd.get('field_capacity_vol_pct', 0):.1f}/{hyd.get('wilting_point_vol_pct', 0):.1f}"
        roots = "REACHED" if h.get("roots_present") else "below"
        print(
            f"  {h['depth_label']:<9} {h['ph']:>5.2f} {cs:>10} {fc_wp:>11} "
            f"{h['volumetric_moisture_pct']:>7.1f}% {str(h.get('usda_texture', '')):<14} {roots}"
        )


def _print_update_frequencies(freq: dict, sensor_fusion: dict | None = None) -> None:
    print("\n[C] COMBINED SATELLITE LAYER UPDATE FREQUENCIES & SENSOR FUSION")
    combined_parcel_dt = (sensor_fusion or {}).get("combined_parcel_dt_days") or freq.get("combined_parcel_dt_days")
    print(
        f"  • Cloud Cover: {freq.get('cloud_cover_pct')}% (p_cloud={freq.get('p_cloud')}) | "
        f"Bare Soil: {freq.get('is_bare_soil')} | "
        f"Combined Parcel dt_cal (S1+S2+L8/9): {combined_parcel_dt} d"
    )
    if sensor_fusion:
        mf = sensor_fusion.get("moisture_fusion_3way") or {}
        print(
            f"  • 3-Way Inverse-Variance Moisture Fusion: {mf.get('fused_value')}% vol. "
            f"(fused_sigma=±{mf.get('fused_sigma')}% vs min single-sensor ±{mf.get('min_input_sigma')}%, "
            f"-{mf.get('variance_reduction_pct')}% var) | "
            f"Conserved Mean: {sensor_fusion.get('parcel_mean_moisture_conserved_pct')}%"
        )
    layers = freq.get("layers") or {}
    print(f"  {'Layer / Sensor':<30} {'Res':>7} {'dt_tick':>9} {'dt_cal':>9} {'Notes'}")
    print("  " + "-" * 74)
    for key in (
        "sentinel2_l2a",
        "sentinel1_sar",
        "landsat_8_9",
        "copernicus_dem_glo30",
        "smap_lband",
        "hlsl30",
        "ecostress",
        "bare_soil_swir_ph",
        "fao56_root_zone",
    ):
        lyr = layers.get(key)
        if not lyr:
            continue
        res = f"{lyr['resolution_m']}m" if lyr.get("resolution_m") else "-"
        if lyr.get("t_orbit_days") is not None:
            dt_tick = f"{lyr['t_orbit_days']:.1f}d"
        elif lyr.get("dt_tick_hours") is not None:
            dt_tick = f"{lyr['dt_tick_hours']:.0f}h"
        else:
            dt_tick = "-"
        raw_dt_cal = lyr.get("dt_clean_days")
        if isinstance(raw_dt_cal, (int, float)):
            dt_cal = f"{raw_dt_cal:.2f}d"
        elif raw_dt_cal is not None:
            dt_cal = str(raw_dt_cal)
        else:
            dt_cal = "dormant"
        note = "cloud-piercing" if lyr.get("cloud_piercing") else "optical (cloud-adj)"
        if key == "bare_soil_swir_ph":
            note = "active (NDVI<0.20)" if lyr.get("active") else "dormant (canopy closed)"
        print(f"  {lyr['sensor']:<30} {res:>7} {dt_tick:>9} {dt_cal:>9} {note}")


def _print_live_monitor(live_mon: dict) -> None:
    plain = live_mon.get("plain_rotations") or []
    ease = live_mon.get("easiness_rotations") or []
    t_now = live_mon.get("t_now_day", 0)
    print(f"\n[D] LIVE t > 0 ROTATION MONITOR & UNCERTAINTY CONE (t_now = Day {t_now})")
    if not plain:
        print("  • No rotation plans available (no climate dataset for this coordinate).")
        return

    top_p = plain[0]
    ls = top_p.get("live_state") or {}
    tl = top_p.get("timeline") or {}
    print(
        f"  • Monitored Top Sequence : {top_p['name']} | Stage: {ls.get('active_stage')}"
    )
    print(
        f"  • Canopy Assimilation    : Expected NDVI {ls.get('expected_ndvi')} vs Observed "
        f"{ls.get('observed_ndvi')} -> growth_lag_days = {ls.get('growth_lag_days')} d"
    )
    print(
        f"  • Live Expiry Windows    : safe_expiry_date = {ls.get('safe_expiry_date')} "
        f"| hard_expiry_date = {ls.get('hard_expiry_date')}"
    )
    print(
        f"  • Turnaround Collision   : collision_probability_pct = {tl.get('collision_probability_pct')}% "
        f"| Harvest sigma = ±{ls.get('sigma_at_harvest_days')} d"
    )

    cone = ls.get("uncertainty_cone_series") or []
    if cone:
        sample = [cone[0]] + cone[1:-1:max(1, len(cone) // 5)] + ([cone[-1]] if len(cone) > 1 else [])
        print("  • Uncertainty Cone Sample (0..t_now collapsed -> t > t_now expanding):")
        for pt in sample:
            phase = "OBS(past)" if pt["is_observed_past"] else "PROJ(cone)"
            print(
                f"    Day {pt['day']:>3}: {phase:<10} "
                f"nom={pt['nominal_progress_pct']:5.1f}% "
                f"[{pt['pessimistic_bound_pct']:5.1f}% .. {pt['optimistic_bound_pct']:5.1f}%]"
            )

    print("\n[E] SIDE-BY-SIDE DUAL ROTATION COMPARISON")
    top_e = ease[0] if ease else top_p
    em_p = top_p.get("easiness_matrix") or {}
    em_e = top_e.get("easiness_matrix") or {}

    print(f"  1) TOP PLAIN ROTATION (0-100 Biology): #{top_p.get('rank')} {top_p['name']}")
    print(
        f"     Biology Score: {top_p.get('score')}/100 [{top_p.get('rating')}] | "
        f"Ease Score: {em_p.get('easiness_score')}/10 ({em_p.get('easiness_tier')}) | "
        f"Ease-Adj: {top_p.get('ease_adjusted_score')}"
    )

    print(f"  2) TOP EASINESS-MATRIX ROTATION (0-10 Ease): #{top_e.get('ease_rank')} {top_e['name']}")
    print(
        f"     Ease Score: {em_e.get('easiness_score')}/10 [{em_e.get('easiness_tier')}] | "
        f"Biology Score: {top_e.get('score')}/100 | "
        f"Ease-Adj: {top_e.get('ease_adjusted_score')}"
    )
    factors = em_e.get("factors") or {}
    if factors:
        print("     Operational Hardness Breakdown (0=easy, 10=hard):")
        for k, v in factors.items():
            print(f"       - {k:<28}: {v}/10")


def run_3d_demo(
    zone_name: str,
    country: str,
    lat: float,
    lon: float,
    boundary: dict | None,
    windows: tuple[Window, ...],
    t_now_day: int,
    observed_ndvi: float | None,
    offline: bool,
    render_png: str | None = None,
) -> None:
    print("=" * 78)
    print("AGROSHIFT 3D FIELD SLAB & LIVE t > 0 ROTATION MONITOR")
    print(f"Zone: {zone_name} | Lat {lat:.4f}, Lon {lon:.4f} ({country}) | t_now=Day {t_now_day} | offline={offline}")
    print("=" * 78)

    req = request_parameters(lat, lon, date(2001, 1, 1), date(2025, 12, 31))
    ds = archived_history(req) if offline else load_history(lat, lon)

    af_res = derive_field_autofill(lat, lon, country, boundary=boundary, dataset=ds, offline=offline)
    af = af_res.get("autofill", {})
    area_ha = (af.get("area_ha") or {}).get("value")
    ph_val = (af.get("ph") or {}).get("value")
    drainage = (af.get("drainage") or {}).get("value") or "well_drained"

    if ds is not None:
        farm = Farm(
            country=country,
            latitude=lat,
            longitude=lon,
            area_ha=area_ha,
            windows=windows,
            ph=ph_val,
            drainage=drainage,
            irrigation="rainfed",
        )
        plans = plan_global_rotations(farm, ds, max_sequences=6)
    else:
        plans = []

    live_mon = evaluate_live_rotation_state(
        plans,
        t_now_day=t_now_day,
        observed_ndvi=observed_ndvi,
        weather_volatility=0.18,
    )

    plain = live_mon.get("plain_rotations") or []
    if plain:
        top_live = plain[0].get("live_state") or {}
        active_root = float(top_live.get("active_root_depth_m", 0.45))
        ndvi_curr = observed_ndvi if observed_ndvi is not None else float(top_live.get("expected_ndvi") or 0.58)
    else:
        active_root = 0.45
        ndvi_curr = observed_ndvi if observed_ndvi is not None else 0.58

    slab_3d = build_3d_field_slab(
        lat,
        lon,
        country,
        boundary=boundary,
        area_ha=area_ha,
        dataset=ds,
        active_root_depth_m=active_root,
        ndvi_current=ndvi_curr,
        offline=offline,
    )

    _print_terrain_mesh(slab_3d["terrain_3d_mesh"])
    _print_soil_horizons(slab_3d["soil_3d_horizons"], slab_3d["active_root_depth_m"])
    _print_update_frequencies(slab_3d["update_frequencies"], slab_3d.get("sensor_fusion"))
    _print_live_monitor(live_mon)

    if render_png:
        saved = render_3d_monitor_png(
            slab_3d,
            live_mon,
            render_png,
            title=f"AGROSHIFT 3D FIELD LAB  |  {zone_name}  |  Live t_now = Day {t_now_day}",
        )
        print(f"\n[PNG] Saved 3D render -> {saved}")

    print("\n" + "=" * 78)
    print("3D MONITOR DEMO COMPLETE.")
    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser(description="AgroShift 3D Field Slab & Live Rotation Monitor CLI")
    parser.add_argument("--random", action="store_true", help="Pick a random global agricultural zone and t_now_day")
    parser.add_argument("--preset", choices=list(GLOBAL_ZONES.keys()), default="anuradhapura", help="Named zone preset")
    parser.add_argument("--lat", type=float, help="Custom latitude")
    parser.add_argument("--lon", type=float, help="Custom longitude")
    parser.add_argument(
        "--coords",
        type=str,
        default=None,
        help="Semicolon-separated lat,lon polygon vertices, e.g. '8.3145,80.4211;8.3169,80.4234;...'",
    )
    parser.add_argument("--country", type=str, default="LK", help="ISO country code")
    parser.add_argument("--t-now", type=int, default=None, help="Live observation day (default: 42)")
    parser.add_argument("--ndvi", type=float, default=None, help="Observed HLS/Sentinel NDVI")
    parser.add_argument("--offline", action="store_true", help="Force offline mode")
    parser.add_argument("--render-png", type=str, default=None, help="Output PNG path for 3D Field Slab + Telemetry render")
    args = parser.parse_args()

    if args.coords:
        pts: list[tuple[float, float]] = []
        for pair in args.coords.split(";"):
            pair = pair.strip()
            if not pair:
                continue
            lat_s, lon_s = pair.split(",")
            pts.append((float(lat_s.strip()), float(lon_s.strip())))
        if len(pts) < 3:
            raise SystemExit("--coords requires at least 3 'lat,lon' pairs separated by ';'")
        ring = [[p_lon, p_lat] for p_lat, p_lon in pts]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        lat = round(sum(p[0] for p in pts) / len(pts), 6)
        lon = round(sum(p[1] for p in pts) / len(pts), 6)
        name = f"Custom {len(pts)}-Vertex Parcel ({lat:.4f}, {lon:.4f})"
        country = args.country.upper()
        boundary = {"type": "Polygon", "coordinates": [ring]}
        windows = (Window(10, 1, 1, 20), Window(3, 1, 6, 30))
        t_now = args.t_now if args.t_now is not None else 42
        obs_ndvi = args.ndvi
    elif args.lat is not None and args.lon is not None:
        name = f"Custom Coordinate ({args.lat:.4f}, {args.lon:.4f})"
        country = args.country.upper()
        lat, lon = args.lat, args.lon
        boundary = None
        windows = (Window(3, 1, 6, 30), Window(10, 1, 1, 20))
        t_now = args.t_now if args.t_now is not None else 42
        obs_ndvi = args.ndvi
    elif args.random:
        zone_key = random.choice(list(GLOBAL_ZONES.keys()))
        z = GLOBAL_ZONES[zone_key]
        name = z["name"]
        country = z["country"]
        lat, lon = z["lat"], z["lon"]
        boundary = z["polygon"]
        windows = z["windows"]
        t_now = args.t_now if args.t_now is not None else random.randint(21, 63)
        obs_ndvi = args.ndvi if args.ndvi is not None else round(random.uniform(0.32, 0.78), 2)
    else:
        z = GLOBAL_ZONES[args.preset]
        name = z["name"]
        country = z["country"]
        lat, lon = z["lat"], z["lon"]
        boundary = z["polygon"]
        windows = z["windows"]
        t_now = args.t_now if args.t_now is not None else 42
        obs_ndvi = args.ndvi

    run_3d_demo(name, country, lat, lon, boundary, windows, t_now, obs_ndvi, args.offline, render_png=args.render_png)


if __name__ == "__main__":
    main()
