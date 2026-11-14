"""Opt-in real PostgreSQL transaction, RLS and history checks; creates a disposable database."""

from contextlib import closing
from dataclasses import asdict
import os
import uuid
import pytest


def test_private_repository_isolation_conflicts_and_history():
    admin_dsn = os.getenv("AGROSHIFT_TEST_PG_ADMIN")
    if not admin_dsn:
        pytest.skip("Set AGROSHIFT_TEST_PG_ADMIN on a disposable PostgreSQL cluster")
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from agroshift.knowledge_store import ROOT, postgres_connect, migrate
    from agroshift.private_store import PrivateStore
    from agroshift.farm_records import profile
    from agroshift.assistant import DEMO_SCENARIOS
    from agroshift.power import DataError

    salt = uuid.uuid4().hex[:12]
    db, role = "farmtest_" + salt, "farmrole_" + salt
    password = uuid.uuid4().hex
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db)))
        try:
            admin.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {}"
                ).format(sql.Identifier(role), sql.Literal(password))
            )
            with closing(postgres_connect(make_conninfo(admin_dsn, dbname=db))) as conn:
                migrate(conn)
                migrate(conn)
                conn.execute(
                    (ROOT / "db/server_access.sql")
                    .read_text()
                    .replace("TO agroshift_app", "TO " + role)
                )
            dsn = make_conninfo(admin_dsn, dbname=db, user=role, password=password)
            a, b = PrivateStore(dsn, uuid.uuid4()), PrivateStore(dsn, uuid.uuid4())
            value = profile(
                "Private field",
                DEMO_SCENARIOS["scenario_1_well_drained"]["farm"],
                "Anuradhapura",
            )
            row = a.save_farm(value)
            assert len(a.farms()) == 1 and b.farms() == []
            a.account("Alice")
            assert a.account() == "Alice" and b.account() == ""
            updated = a.save_farm(
                dict(value, name="Renamed"), row["id"], row["revision"]
            )
            assert updated["revision"] == 2
            with pytest.raises(DataError, match="changed"):
                a.save_farm(value, row["id"], row["revision"])
            with pytest.raises(DataError, match="changed"):
                b.save_farm(value, row["id"], 2)
            report = {
                "schema": "agroshift.crop-finder.v1",
                "farm": value["farm"],
                "options": [],
                "generated_at": "2026-11-08T00:00:00Z",
            }
            a.save_analysis(row["id"], report)
            a.save_analysis(
                row["id"], dict(report, generated_at="2026-11-08T01:00:00Z")
            )
            assert len(a.history(row["id"])) == 1 and b.history(row["id"]) == []
            with pytest.raises(DataError, match="no longer available"):
                b.save_analysis(row["id"], report)
            with b.connection() as conn:
                assert (
                    conn.execute(
                        "UPDATE farm_profiles SET profile='{}' WHERE id=%s",
                        (row["id"],),
                    ).rowcount
                    == 0
                )
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute(
                        "INSERT INTO farm_profiles(owner_id,profile) VALUES (%s,'{}')",
                        (a.owner,),
                    )
            with closing(postgres_connect(dsn)) as conn:
                assert conn.execute("SELECT * FROM farm_profiles").fetchall() == []
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute("DELETE FROM saved_analyses")
            with pytest.raises(DataError, match="restricted"):
                PrivateStore(make_conninfo(admin_dsn, dbname=db), a.owner).farms()
        finally:
            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(db)))
            admin.execute(
                sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role))
            )
