"""Bounded database queries for reviewed crop references and multilingual names."""

from contextlib import closing
from functools import lru_cache
import os
from pathlib import Path
import sqlite3
import threading
import time

from agroshift.science.knowledge.knowledge_store import (
    migrate,
    is_postgres,
    postgres_connect,
    release_files,
    run,
    search_key,
    seed_database,
    sqlite_connect,
)

_LOCK = threading.RLock()


def _cache_path():
    configured = os.getenv("AGROSHIFT_KNOWLEDGE_PATH")
    if configured:
        return Path(configured).expanduser()
    base = Path(
        os.getenv("XDG_CACHE_HOME")
        or os.getenv("LOCALAPPDATA")
        or Path.home() / ".cache"
    )
    return base / "agroshift" / "knowledge.sqlite3"


@lru_cache(maxsize=4)
def _prepare_offline(path, signature, managed):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite_connect(path)) as conn:
        migrate(conn)
        if (
            not managed
            or not conn.execute("SELECT 1 FROM ag_pack WHERE id='global'").fetchone()
        ):
            seed_database(conn)


def _execute(conn, kind, values):
    if kind == "traits":
        return [
            dict(row)
            for row in run(
                conn,
                "SELECT * FROM ag_global_trait_named"
                + (" WHERE crop_id=?" if values else "")
                + " ORDER BY crop_id,trait,source_id",
                values,
            )
        ]
    if kind == "growth_stages":
        return [
            dict(row)
            for row in run(
                conn,
                "SELECT * FROM ag_growth_stage_reviewed"
                + (" WHERE crop_id=?" if values else "")
                + " ORDER BY crop_id,stage_order",
                values,
            )
        ]
    if kind == "pest_context":
        return [
            dict(row)
            for row in run(
                conn,
                "SELECT * FROM ag_pest_context_reviewed"
                + (" WHERE crop_id=?" if values else "")
                + " ORDER BY crop_id,category,agent_name",
                values,
            )
        ]
    if kind == "cultivar_traits":
        return [
            dict(row)
            for row in run(
                conn,
                "SELECT * FROM ag_cultivar_trait_reviewed"
                + (" WHERE crop_id=?" if values else "")
                + " ORDER BY crop_id,cultivar_id,trait",
                values,
            )
        ]
    if kind == "soil_observations":
        return [
            dict(row)
            for row in run(
                conn,
                "SELECT * FROM ag_soil_observation"
                + (" WHERE country_code=?" if values else "")
                + " ORDER BY profile_code,upper_depth_cm,property",
                values,
            )
        ]
    if kind == "refresh_policies":
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM ag_refresh_policy ORDER BY dataset_id"
            )
        ]
    if kind == "versions":
        return {
            row["id"]: row["version"]
            for row in conn.execute("SELECT id,version FROM ag_pack")
        }
    if kind == "by_id":
        return [
            dict(row)
            for row in run(conn, "SELECT * FROM ag_catalogue_cited WHERE id=?", values)
        ]
    if kind == "candidates":
        marks = ",".join("?" for _ in values)
        return [
            dict(row)
            for row in run(
                conn,
                f"SELECT * FROM ag_catalogue_cited WHERE id IN ({marks}) ORDER BY name,id",
                values,
            )
        ]
    if kind == "categories":
        return [
            row["group_name"]
            for row in conn.execute(
                "SELECT DISTINCT group_name FROM ag_catalogue_cited WHERE group_name IS NOT NULL ORDER BY group_name"
            )
        ]
    query, limit, offset, category = values
    where = ""
    params = []
    if query:
        token = 'token COLLATE "C"' if is_postgres(conn) else "token"
        where = f" WHERE c.id IN (SELECT crop_id FROM ag_name_token WHERE {token}>=? AND {token}<?)"
        params.extend((query, query + chr(0x10FFFF)))
    if category:
        where += (" AND " if where else " WHERE ") + "c.group_name=?"
        params.append(category)
    if kind == "count":
        return run(
            conn, "SELECT count(*) AS total FROM ag_catalogue_cited c" + where, params
        ).fetchone()["total"]
    return [
        dict(row)
        for row in run(
            conn,
            "SELECT c.* FROM ag_catalogue_cited c"
            + where
            + " ORDER BY c.name,c.id LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
    ]


@lru_cache(maxsize=128)
def _query(kind, values, url, path, signature, minute, managed):
    reason = None
    if url:
        try:
            with closing(postgres_connect(url, readonly=True)) as conn:
                conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
                return _execute(conn, kind, values), "PostgreSQL", None
        except Exception:
            reason = "Shared database unavailable. Using bundled reference data."
    with _LOCK:
        try:
            _prepare_offline(path, signature, managed)
            conn = sqlite_connect(path)
        except (OSError, sqlite3.OperationalError):
            conn = sqlite_connect(":memory:")
            migrate(conn)
            seed_database(conn)
            reason = "Local database unavailable. Using bundled references in memory."
        with closing(conn):
            conn.execute("BEGIN")
            return _execute(conn, kind, values), "Offline SQLite", reason


def _read(kind, values=()):
    signature = tuple(path.stat().st_mtime_ns for _, path in release_files())
    return _query(
        kind,
        tuple(values),
        os.getenv("AGROSHIFT_DATABASE_URL"),
        str(_cache_path()),
        signature,
        int(time.monotonic() // 60),
        bool(os.getenv("AGROSHIFT_KNOWLEDGE_PATH")),
    )


def search_crops(query="", limit=50, offset=0, category=None):
    """Indexed prefix search over whole names and words in translated/scientific names."""
    if (
        type(limit) is not int
        or type(offset) is not int
        or offset < 0
        or not 1 <= limit <= 500
    ):
        raise ValueError("Use a non-negative offset and a limit from 1 to 500.")
    term = search_key(str(query))
    if len(term) > 150:
        raise ValueError("Crop searches may contain up to 150 characters.")
    return [dict(row) for row in _read("search", (term, limit, offset, category))[0]]


def count_crops(query="", category=None):
    term = search_key(str(query))
    if len(term) > 150:
        raise ValueError("Crop searches may contain up to 150 characters.")
    return _read("count", (term, 1, 0, category))[0]


def crop_by_id(crop_id):
    rows = _read("by_id", (crop_id,))[0]
    return dict(rows[0]) if rows else None


def screening_candidates(ids):
    """Fetch just the crop identities with applicable scientific traits."""
    selected = sorted(set(ids))
    rows = []
    for start in range(0, len(selected), 200):
        rows.extend(
            dict(row) for row in _read("candidates", selected[start : start + 200])[0]
        )
    return rows


def global_traits(crop_id=None):
    return [dict(t) for t in _read("traits", (crop_id,) if crop_id else ())[0]]


def growth_stages(crop_id=None):
    return [dict(s) for s in _read("growth_stages", (crop_id,) if crop_id else ())[0]]


def pest_context(crop_id=None):
    return [dict(p) for p in _read("pest_context", (crop_id,) if crop_id else ())[0]]


def cultivar_traits(crop_id=None):
    return [dict(c) for c in _read("cultivar_traits", (crop_id,) if crop_id else ())[0]]


def soil_observations(country_code=None):
    return [dict(o) for o in _read("soil_observations", (country_code.upper(),) if country_code else ())[0]]


def refresh_policies():
    return [dict(p) for p in _read("refresh_policies")[0]]


def knowledge_status():
    versions, backend, reason = _read("versions")
    return dict(backend=backend, fallback_reason=reason, versions=dict(versions))


def clear_cache():
    with _LOCK:
        _query.cache_clear()
        _prepare_offline.cache_clear()


def crop_categories():
    """Only groups present in the active catalogue, not invented UI categories."""
    return list(_read("categories")[0])
