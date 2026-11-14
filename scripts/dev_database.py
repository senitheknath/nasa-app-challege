"""Local PostgreSQL with separate administrator, reference-reader and private-app roles."""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".cache/local-database.json"
ENV = ROOT / ".cache/postgres.env"


def settings(create=False):
    if CONFIG.exists():
        return json.loads(CONFIG.read_text())
    if not create:
        raise SystemExit("Run python -m scripts.dev_database up first.")
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    data = {
        key: secrets.token_urlsafe(32)
        for key in ("admin_password", "reader_password", "app_password")
    }
    CONFIG.write_text(json.dumps(data))
    CONFIG.chmod(0o600)
    return data


def dsn(config, role="reader", database="agroshift"):
    from psycopg.conninfo import make_conninfo

    return make_conninfo(
        host="127.0.0.1",
        port=56542,
        dbname=database,
        user="agroshift_" + role,
        password=config[role + "_password"],
    )


def initialize(config):
    import psycopg
    from psycopg import sql
    from agroshift.knowledge_store import postgres_connect, migrate, seed_database

    deadline = time.monotonic() + 60
    while True:
        try:
            conn = postgres_connect(dsn(config, "admin"))
            break
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise SystemExit(
                    "Local PostgreSQL did not become ready. Check Docker and .cache credentials."
                )
            time.sleep(1)
    with closing(conn):
        migrate(conn)
        seed_database(conn)
        with conn.transaction():
            for role in ("reader", "app"):
                name = "agroshift_" + role
                if not conn.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=%s", (name,)
                ).fetchone():
                    conn.execute(
                        sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS").format(
                            sql.Identifier(name)
                        )
                    )
                conn.execute(
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(name), sql.Literal(config[role + "_password"])
                    )
                )
            conn.execute((ROOT / "db/reference_reader.sql").read_text())
            conn.execute((ROOT / "db/server_access.sql").read_text())
    print("PostgreSQL ready on localhost:56542. Seed and access rules verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "status", "down"])
    args = parser.parse_args()
    config = settings(args.action == "up")
    ENV.write_text("AGROSHIFT_LOCAL_ADMIN_PASSWORD=" + config["admin_password"] + "\n")
    ENV.chmod(0o600)
    command = [
        "docker",
        "compose",
        "--project-name",
        "agroshift-local",
        "--env-file",
        str(ENV),
        "-f",
        str(ROOT / "compose.database.yml"),
    ]
    if args.action == "up":
        subprocess.run([*command, "up", "-d", "--wait"], check=True, cwd=ROOT)
        initialize(config)
    elif args.action == "down":
        subprocess.run([*command, "down"], check=True, cwd=ROOT)
        print("Database stopped; saved data remains in its Docker volume.")
    else:
        subprocess.run([*command, "ps"], check=True, cwd=ROOT)
        from agroshift.knowledge_store import postgres_connect

        with closing(postgres_connect(dsn(config))) as conn:
            count = conn.execute(
                "SELECT count(*) AS n FROM ag_catalogue_cited"
            ).fetchone()["n"]
            print(f"Reference reader verified: {count} crop identities.")


if __name__ == "__main__":
    main()
