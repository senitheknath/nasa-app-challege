"""Manage local development databases. Run as python -m scripts.knowledge_db."""
import argparse
from contextlib import closing
import os
from pathlib import Path

from agroshift.knowledge import _cache_path
from agroshift.knowledge_store import import_file, migrate, postgres_connect, seed_database, sqlite_connect


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["migrate","seed","import-global","status","conflicts"])
    backend = parser.add_mutually_exclusive_group()
    backend.add_argument("--postgres", action="store_true", help="Use AGROSHIFT_IMPORT_DATABASE_URL")
    backend.add_argument("--sqlite", type=Path, help="Local reference file")
    parser.add_argument("--file",type=Path,help="Locally obtained, licensed global crop pack")
    args = parser.parse_args(argv)
    if (args.action == "import-global") != bool(args.file):
        parser.error("Supply --file only with import-global.")
    if args.postgres:
        dsn = os.environ.get("AGROSHIFT_IMPORT_DATABASE_URL")
        if not dsn:
            parser.error("Set AGROSHIFT_IMPORT_DATABASE_URL for an isolated database.")
        conn = postgres_connect(dsn)
    else:
        path = args.sqlite or _cache_path()
        path.parent.mkdir(parents=True,exist_ok=True)
        conn = sqlite_connect(path)
    with closing(conn):
        if args.action in {"seed","migrate","import-global"}:
            migrate(conn)
        if args.action == "seed":
            for pack,result in seed_database(conn).items():
                print(pack,result)
        elif args.action == "import-global":
            print(import_file(conn,"global",args.file))
        elif args.action == "status":
            for row in conn.execute("SELECT id,version,digest FROM ag_pack ORDER BY id"):
                print(dict(row))
            for row in conn.execute("SELECT pack_id,status,finished_at,detail FROM ag_import_history ORDER BY finished_at DESC LIMIT 10"):
                print(dict(row))
        elif args.action == "conflicts":
            for row in conn.execute("""SELECT e.crop_id,e.trait,e.region_id,e.low,e.high,e.value_text,e.units,e.source_url
                   FROM ag_conflicts c JOIN ag_evidence e ON e.id=c.evidence_id ORDER BY e.crop_id,e.trait"""):
                print(dict(row))


if __name__ == "__main__":
    main()
