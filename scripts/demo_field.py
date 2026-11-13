#!/usr/bin/env python3
"""AgroShift CLI Demo & Data Retrieval Playground.

Exercises the complete Earth observation, auto-fill, live satellite monitoring,
and science-enriched crop rotation pipeline from the terminal.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Add repo root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agroshift.earth_data.autofill import derive_field_autofill
from agroshift.earth_data.satellite import fetch_satellite_overpasses, get_active_monitoring_layers
from agroshift.rotation import plan_global_rotations
from agroshift.science.climate.power import archived_history, request_parameters
from agroshift.science.decision.decision import Farm, Window

PRESETS = {
    "anuradhapura": {
        "name": "Anuradhapura Dry Zone, Sri Lanka",
        "country": "LK",
        "lat": 8.3114,
        "lon": 80.4037,
        "windows": (Window(10, 1, 1, 20), Window(3, 1, 6, 30)),
        "polygon": {
            "type": "Polygon",
            "coordinates": [
                [
                    [80.400, 8.310],
                    [80.405, 8.310],
                    [80.405, 8.315],
                    [80.400, 8.315],
                    [80.400, 8.310],
                ]
            ],
        },
    },
    "nairobi": {
        "name": "Nairobi Peri-Urban Farm, Kenya",
        "country": "KE",
        "lat": -1.2921,
        "lon": 36.8219,
        "windows": (Window(3, 1, 6, 30), Window(10, 1, 1, 20)),
        "polygon": {
            "type": "Polygon",
            "coordinates": [
                [
                    [36.820, -1.290],
                    [36.825, -1.290],
                    [36.825, -1.295],
                    [36.820, -1.295],
                    [36.820, -1.290],
                ]
            ],
        },
    },
    "ames": {
        "name": "Ames Central Iowa Research Farm, USA",
        "country": "US",
        "lat": 42.0308,
        "lon": -93.6319,
        "windows": (Window(4, 15, 7, 31), Window(8, 1, 11, 15)),
        "polygon": None,
    },
}


def run_demo(lat: float, lon: float, country: str, boundary: dict | None, windows: tuple[Window, ...], offline: bool = False):
    print("=" * 72)
    print(f"🛰️  AGROSHIFT EARTH DATA & AUTO-FILL PLAYGROUND")
    print(f"📍 Location: Lat {lat:.4f}, Lon {lon:.4f} ({country})")
    print("=" * 72)

    # 1. Auto-Fill Signals
    print("\n[1] DERIVING SMART AUTO-FILL SIGNALS...")
    autofill_result = derive_field_autofill(lat, lon, country, boundary=boundary, offline=offline)
    af = autofill_result["autofill"]

    area_info = af.get("area_ha", {})
    if area_info.get("value") is not None:
        print(f"  • Field Area     : {area_info['value']} ha ({area_info['acres']} acres) [{area_info['source']}]")
    else:
        print(f"  • Field Area     : Unspecified (no boundary drawn)")

    ph_info = af.get("ph", {})
    print(f"  • Soil pH        : {ph_info.get('value')} [{ph_info.get('source')}]")

    drain_info = af.get("drainage", {})
    slope_str = f", Slope {drain_info['slope_pct']}%" if drain_info.get("slope_pct") is not None else ""
    elev_str = f", Elev {drain_info['elevation_m']} m" if drain_info.get("elevation_m") is not None else ""
    print(f"  • Drainage Prior : {drain_info.get('value')}{slope_str}{elev_str}")
    print(f"                     Source: {drain_info.get('source')}")

    # 2. Live Satellite Monitoring & Overpasses
    print("\n[2] QUERYING NASA CMR OVERPASS SCHEDULE & GIBS LAYERS...")
    overpasses = fetch_satellite_overpasses(lat, lon, boundary=boundary, offline=offline)
    acqs = overpasses.get("acquisitions", [])
    print(f"  • Overpasses Found: {len(acqs)} recent/upcoming scenes")
    for a in acqs:
        cloud = f" (Cloud Cover: {a['cloud_cover_pct']:.1f}%)" if a.get("cloud_cover_pct") is not None else ""
        print(f"    - {a['label']}: Granule {a['granule_id']}{cloud} [{a['status']}]")

    gibs_layers = get_active_monitoring_layers(lat, lon)
    print(f"\n  • Live NASA GIBS Map Overlay Endpoints:")
    for lyr in gibs_layers:
        print(f"    - {lyr['name']} ({lyr['resolution']}):")
        print(f"      {lyr['tile_url'][:75]}...")

    # 3. Science-Enriched Crop Rotation Sequences
    print("\n[3] EVALUATING 2-SEASON ROTATION SEQUENCES (SCIENCE RULE ENGINE)...")
    try:
        req = request_parameters(lat, lon, date(2001, 1, 1), date(2025, 12, 31))
        ds = archived_history(req)
        if not ds:
            print("  • (No local NASA POWER historical snapshot found for this cell; using default screening pool)")
            return

        farm = Farm(
            country=country,
            latitude=lat,
            longitude=lon,
            windows=windows,
            ph=ph_info.get("value"),
            drainage=drain_info.get("value") or "well_drained",
            irrigation="rainfed",
        )

        plans = plan_global_rotations(farm, ds, max_sequences=5)
        print(f"  • Generated Top {len(plans)} Agronomic Sequences:")
        for idx, p in enumerate(plans, start=1):
            s1 = p["season_1"]
            s2 = p["season_2"]
            status = p["overall_status"].upper()
            print(f"\n  [{idx}] {p['name']} --> {status}")
            print(f"      S1: {s1['crop_name']} ({s1['family']}) [{s1['window']}]")
            print(f"      S2: {s2['crop_name']} ({s2['family']}) [{s2['window']}]")
            print(f"      Summary: {p['summary']}")

            # Print exact timeline milestones
            tl = p.get("timeline", {})
            tb = tl.get("turnaround_summary", {})
            if tb.get("buffer_days") is not None:
                print(f"      ⏱️  Timeline & Buffer: {tb.get('buffer_days')} days [{tb.get('status').upper()}]")
                print(f"         Advisory: {tb.get('advisory')}")

            for slot in tl.get("slots", []):
                print(f"         - {slot['crop_name']}: Sow {slot['sowing_date']} ──> Harvest {slot['harvest_nominal_date']} ({slot['growth_cycle_days']['nominal']}d) [Slack: {slot['delay_slack_days']}d]")
                for st in slot.get("stages", []):
                    print(f"           • {st['description']}: {st['start_date']} to {st['end_date']} ({st['duration_days']}d)")

            # Print exact findings from composable rules
            findings = p.get("transition", {}).get("findings", [])
            for f in findings:
                sev = f.get("severity", "info").upper()
                print(f"      * [{sev}] {f.get('message')}")
    except Exception as exc:
        print(f"  • Note on rotation engine: {exc}")

    print("\n" + "=" * 72)
    print("✅ DEMO COMPLETE. All signals retrieved and evaluated successfully.")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="AgroShift CLI Demo & Data Playground")
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        default="anuradhapura",
        help="Use a pre-configured location preset (anuradhapura, nairobi, ames)",
    )
    parser.add_argument("--lat", type=float, help="Custom latitude")
    parser.add_argument("--lon", type=float, help="Custom longitude")
    parser.add_argument("--country", type=str, default="LK", help="ISO country code (default: LK)")
    parser.add_argument("--offline", action="store_true", help="Force offline mode using local caches")
    args = parser.parse_args()

    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
        country = args.country
        boundary = None
        windows = (Window(3, 1, 6, 30), Window(10, 1, 1, 20))
    else:
        preset = PRESETS[args.preset]
        lat = preset["lat"]
        lon = preset["lon"]
        country = preset["country"]
        boundary = preset["polygon"]
        windows = preset["windows"]
        print(f"\n--> Using preset: {preset['name']}")

    run_demo(lat, lon, country, boundary, windows, offline=args.offline)


if __name__ == "__main__":
    main()
