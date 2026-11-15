"""Optional live PostgreSQL check using a disposable cluster with an isolated administrator."""
from contextlib import closing
import os
from pathlib import Path
import uuid

import pytest

from agroshift.knowledge_store import ROOT, migrate, postgres_connect, import_file


def test_postgres_migrations_reference_permissions_and_tenant_isolation():
    # This opt-in test needs CREATEDB and CREATEROLE, and creates a random DB and roles.
    dsn = os.getenv("AGROSHIFT_TEST_PG_ADMIN")
    if not dsn:
        pytest.skip("Set AGROSHIFT_TEST_PG_ADMIN on a disposable test cluster")
    psycopg = pytest.importorskip("psycopg")
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    salt = uuid.uuid4().hex[:12]
    db, tenant, reader = (f"agtest_{v}_{salt}" for v in ("db","tenant","reader"))
    alice,bob = uuid.uuid4(),uuid.uuid4()
    identifier = sql.Identifier
    with psycopg.connect(dsn,autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(identifier(db)))
        try:
            for role in (tenant,reader):
                admin.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(identifier(role)))
            with closing(postgres_connect(make_conninfo(dsn,dbname=db))) as conn:
                migrate(conn)
                migrate(conn)
                import_file(conn,"lk",ROOT/"data/crops.json")
                conn.execute("CREATE SCHEMA auth")
                # Reproduce the contract Supabase supplies to RLS from its verified JWT.
                conn.execute("""CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE SQL STABLE
                    AS $$ SELECT nullif(current_setting('request.jwt.claim.sub', true),'')::uuid $$""")
                adapter=(ROOT/"db/supabase_authenticated.sql").read_text()
                conn.execute(adapter.replace(" TO authenticated",f" TO {tenant}"))
                grants=(ROOT/"db/reference_reader.sql").read_text()
                conn.execute(grants.replace("TO agroshift_reader",f"TO {reader}"))
                conn.execute(sql.SQL("SET ROLE {}").format(identifier(reader)))
                assert len(conn.execute("SELECT * FROM ag_catalogue_cited").fetchall()) == 5
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute("SELECT * FROM farm_profiles")
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute("DELETE FROM ag_crop_name")
                conn.execute("RESET ROLE")
                conn.execute(sql.SQL("SET ROLE {}").format(identifier(tenant)))
                conn.execute("SELECT set_config('request.jwt.claim.sub',%s,false)",(str(alice),))
                farm=conn.execute("INSERT INTO farm_profiles(owner_id,profile) VALUES (%s,'{}') RETURNING id",(alice,)).fetchone()["id"]
                conn.execute("INSERT INTO saved_analyses(owner_id,farm_id,report) VALUES (%s,%s,'{}')",(alice,farm))
                conn.execute("SELECT set_config('request.jwt.claim.sub',%s,false)",(str(bob),))
                conn.execute("SELECT set_config('agroshift.owner_id',%s,false)",(str(alice),))
                assert conn.execute("SELECT * FROM farm_profiles").fetchall() == []
                assert conn.execute("SELECT * FROM saved_analyses").fetchall() == []
                assert conn.execute("UPDATE farm_profiles SET profile='{}' WHERE id=%s",(farm,)).rowcount == 0
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    conn.execute("INSERT INTO farm_profiles(owner_id,profile) VALUES (%s,'{}')",(alice,))
                with pytest.raises(psycopg.errors.ForeignKeyViolation):
                    conn.execute("INSERT INTO saved_analyses(owner_id,farm_id,report) VALUES (%s,%s,'{}')",(bob,farm))
        finally:
            admin.execute(sql.SQL("DROP DATABASE {}").format(identifier(db)))
            for role in (tenant,reader):
                admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(identifier(role)))
