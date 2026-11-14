"""Exercise actual storage, provenance boundaries and atomic release changes."""
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import sqlite3

import pytest

from agroshift import knowledge
from agroshift.knowledge_store import ROOT, import_file, migrate, sqlite_connect


@pytest.fixture
def catalogue():
    # Fixture numbers only test data plumbing and never enter a bundled reference pack.
    return {
        "version":"test.1","retrieved_on":"2026-11-08",
        "sources":[{"id":"fixture","title":"Test reference","url":"https://example.org/test","license":"fixture only"}],
        "crops":[{"id":"test","name":"Test plant","scientific_name":None,"group":"Fixture plants",
                  "names":[{"language":"es","name":"Frijól de prueba","source_id":"fixture"}]},
                 {"id":"other","name":"Other plant","group":"Fixture plants"}],
        "traits":[{"crop_id":"test","trait":"test_range","min":1,"max":5,"unit":"test units",
                  "source_id":"fixture","region_id":"global","evidence_type":"test evidence",
                  "review_status":"reviewed","note":"Fixture only."}]
    }


def load(conn, tmp_path, doc):
    path = tmp_path / "release.json"
    path.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
    return import_file(conn,"global",path)


def test_reimport_conflicts_and_updated_records(tmp_path,catalogue):
    catalogue["crops"][0].update(family="Testaceae",family_source_id="fixture",family_reference="https://example.org/taxon/1")
    with closing(sqlite_connect(tmp_path/"db")) as conn:
        migrate(conn)
        assert load(conn,tmp_path,catalogue) == "imported"
        assert load(conn,tmp_path,catalogue) == "unchanged"
        assert conn.execute("SELECT count(*) FROM ag_import_history").fetchone()[0] == 1
        assert conn.execute("SELECT support_level FROM ag_catalogue WHERE id='other'").fetchone()[0] == "catalogue"
        assert conn.execute("SELECT family_reference FROM ag_catalogue_cited WHERE id='test'").fetchone()[0] == "https://example.org/taxon/1"
        conflict = deepcopy(catalogue)
        conflict["version"] = "test.2"
        conflict["sources"].append(dict(conflict["sources"][0],id="other-source",url="https://example.org/two"))
        conflict["traits"].append(dict(conflict["traits"][0],source_id="other-source",min=2))
        load(conn,tmp_path,conflict)
        assert conn.execute("SELECT count(*) FROM ag_conflicts").fetchone()[0] == 2
        assert not conn.execute("SELECT * FROM ag_global_trait").fetchall()
        fixed = dict(conflict,version="test.3",traits=conflict["traits"][1:])
        load(conn,tmp_path,fixed)
        record = dict(conn.execute("SELECT * FROM ag_global_trait").fetchone())
        assert (record["low"],record["source_url"],record["version"],record["retrieved_on"]) == (2,"https://example.org/two","test.3","2026-11-08")
        assert conn.execute("SELECT count(*) FROM ag_conflicts").fetchone()[0] == 0


def test_failed_import_preserves_previous_release_and_audit(tmp_path,catalogue):
    with closing(sqlite_connect(tmp_path/"db")) as conn:
        migrate(conn)
        load(conn,tmp_path,catalogue)
        bad = deepcopy(catalogue)
        bad["version"] = "test.2"
        bad["traits"][0]["max"] = -2
        with pytest.raises(ValueError,match="ordered"):
            load(conn,tmp_path,bad)
        with pytest.raises(ValueError,match="released version"):
            load(conn,tmp_path,dict(catalogue,traits=[]))
        assert conn.execute("SELECT version FROM ag_pack WHERE id='global'").fetchone()[0] == "test.1"
        assert conn.execute("SELECT count(*) FROM ag_global_trait").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM ag_import_history WHERE status='failed'").fetchone()[0] == 2
        # Reopen and migrate the file a second time to verify restart and migration idempotency.
    with closing(sqlite_connect(tmp_path/"db")) as conn:
        migrate(conn)
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_missing_scope_and_unreviewed_evidence(tmp_path,catalogue):
    with closing(sqlite_connect(":memory:")) as conn:
        migrate(conn)
        regional = ROOT/"data/crops.json"
        import_file(conn,"lk",regional)
        traits = conn.execute("SELECT e.crop_id,c.name FROM ag_evidence e JOIN ag_cultivar c ON c.id=e.cultivar_id").fetchall()
        assert [(r[0],r[1]) for r in traits] == [("mung_bean","MI 6")]
        assert not conn.execute("SELECT * FROM ag_evidence WHERE crop_id='maize' AND trait='temperature_c'").fetchall()
        assert not conn.execute("SELECT * FROM ag_global_trait").fetchall()
        catalogue["traits"][0]["review_status"]="pending"
        load(conn,tmp_path,catalogue)
        assert not conn.execute("SELECT * FROM ag_global_trait").fetchall()
        assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='farm_profiles'").fetchone() is None


def test_catalogue_offline_outage_and_custom_snapshot(tmp_path,monkeypatch,catalogue):
    path = tmp_path/"knowledge.sqlite3"
    with closing(sqlite_connect(path)) as conn:
        migrate(conn)
        import_file(conn,"lk",ROOT/"data/crops.json")
        load(conn,tmp_path,catalogue)
    monkeypatch.setenv("AGROSHIFT_KNOWLEDGE_PATH",str(path))
    monkeypatch.setenv("AGROSHIFT_DATABASE_URL","invalid value containing an example secret")
    monkeypatch.setattr(knowledge,"release_files",lambda: (("lk",ROOT/"data/crops.json"),))
    knowledge.clear_cache()
    assert [r["id"] for r in knowledge.search_crops("frijol")] == ["test"]
    assert knowledge.search_crops("TEsT plant",limit=1)[0]["support_level"]=="general"
    assert knowledge.search_crops("frijol",offset=1) == []
    assert knowledge.global_traits()[0]["scope"]=="global"
    assert knowledge.knowledge_status()["backend"]=="Offline SQLite"
    assert "secret" not in knowledge.knowledge_status()["fallback_reason"]
    knowledge.clear_cache()


def test_foreign_key_and_source_checks(tmp_path,catalogue):
    with closing(sqlite_connect(":memory:")) as conn:
        migrate(conn)
        bad = deepcopy(catalogue)
        bad["crops"][0]["names"][0]["source_id"]="missing"
        with pytest.raises(sqlite3.IntegrityError):
            load(conn,tmp_path,bad)
        catalogue["traits"][0]["region_id"] = "lk"
        with pytest.raises(ValueError,match="global scope"):
            load(conn,tmp_path,catalogue)



def test_large_catalogue_uses_indexed_bounded_search(tmp_path, catalogue, monkeypatch):
    catalogue["crops"]=[{"id":f"test-{i:04d}","name":f"Plant {i:04d}","group":"Fixture only"} for i in range(1000)]
    catalogue["traits"]=[]
    path=tmp_path/"large.sqlite"
    with closing(sqlite_connect(path)) as conn:
        migrate(conn)
        load(conn,tmp_path,catalogue)
        query=conn.execute("EXPLAIN QUERY PLAN SELECT crop_id FROM ag_name_token WHERE token>=? AND token<?",("plant","planu")).fetchall()
        assert any("ag_token_search" in str(tuple(row)) for row in query)
    monkeypatch.delenv("AGROSHIFT_DATABASE_URL",raising=False)
    monkeypatch.setenv("AGROSHIFT_KNOWLEDGE_PATH",str(path))
    knowledge.clear_cache()
    assert knowledge.count_crops("plant")==1000
    rows=knowledge.search_crops("plant",limit=10,offset=990)
    assert len(rows)==10 and rows[0]["id"]=="test-0990"
    assert knowledge.search_crops("0999")[0]["id"]=="test-0999"
    assert knowledge.crop_by_id("test-0999")["name"]=="Plant 0999"
    assert knowledge.screening_candidates(["test-0999","missing"])[0]["id"]=="test-0999"
    knowledge.clear_cache()
