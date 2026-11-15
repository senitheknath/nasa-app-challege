#!/usr/bin/env python3
"""On-demand full database update command: seeds base packs + pulls FAO EcoCrop & Crop Calendar APIs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agroshift.science.knowledge.enrichment import update_full_database  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Update full AgroShift crop knowledge database on request")
    parser.add_argument("--offline", action="store_true", help="Use cached EcoCrop/Calendar files without network calls")
    parser.add_argument("--countries", nargs="+", default=["LK", "KE"], help="ISO-2 countries for FAO Crop Calendar")
    parser.add_argument("--db", type=str, default=None, help="Target SQLite path (default: data/knowledge.sqlite)")
    args = parser.parse_args()

    res = update_full_database(
        db_path=Path(args.db) if args.db else None,
        allow_network=not args.offline,
        countries=tuple(c.upper() for c in args.countries),
    )
    print("=" * 72)
    print("AGROSHIFT FULL DATABASE UPDATE COMPLETE")
    print("=" * 72)
    print(f"  Database Path          : {res['db_path']}")
    print(f"  EcoCrop Species Loaded : {res['ecocrop_species_loaded']}")
    print(f"  EcoCrop Traits Added   : {res['ecocrop_traits_added']}")
    print(f"  Calendar Rows Added    : {res['calendar_rows_added']}")
    print(f"  Validation Rows Added  : {res['validation_rows_added']}")
    print(f"  Support Tiers Before   : {res['tiers_before']}")
    print(f"  Support Tiers After    : {res['tiers_after']}")


if __name__ == "__main__":
    main()
