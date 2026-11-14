"""Universal spatial GeoCache for environmental, soil, and satellite observations.

Stores cell-based environmental records in a local SQLite database so any query
is cached, transparent, queryable with standard SQL, and manually updatable.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / ".cache" / "geo_cache.db"
_LOCAL_LOCK = threading.Lock()


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return an initialized SQLite connection with foreign keys and WAL mode."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS geo_cache (
                cell_key TEXT PRIMARY KEY,
                data_type TEXT NOT NULL,
                lat_cell REAL NOT NULL,
                lon_cell REAL NOT NULL,
                source TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_geo_cache_type_cell ON geo_cache(data_type, lat_cell, lon_cell)"
        )


def cell_key(data_type: str, latitude: float, longitude: float, precision: int = 3) -> str:
    """Format a cell key rounded to precision decimals (precision 3 ≈ 110 meters)."""
    lat_r = round(float(latitude), precision)
    lon_r = round(float(longitude), precision)
    return f"{data_type}:{lat_r:.{precision}f}:{lon_r:.{precision}f}"


def get_cached(
    data_type: str,
    latitude: float,
    longitude: float,
    *,
    precision: int = 3,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    """Retrieve a cached record by cell key, or None if not found."""
    key = cell_key(data_type, latitude, longitude, precision=precision)
    with _LOCAL_LOCK:
        try:
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload_json, source, updated_at FROM geo_cache WHERE cell_key = ?",
                (key,),
            )
            row = cursor.fetchone()
            if row:
                data = json.loads(row["payload_json"])
                return {
                    "data": data,
                    "source": row["source"],
                    "updated_at": row["updated_at"],
                    "cached": True,
                }
        except Exception:
            return None
    return None


def set_cached(
    data_type: str,
    latitude: float,
    longitude: float,
    payload: Any,
    *,
    source: str = "direct_api",
    precision: int = 3,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Store or update a payload into the spatial cache."""
    key = cell_key(data_type, latitude, longitude, precision=precision)
    lat_r = round(float(latitude), precision)
    lon_r = round(float(longitude), precision)
    payload_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat()

    with _LOCAL_LOCK:
        try:
            conn = get_connection(db_path)
            with conn:
                conn.execute(
                    """
                    INSERT INTO geo_cache (cell_key, data_type, lat_cell, lon_cell, source, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(cell_key) DO UPDATE SET
                        source = excluded.source,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (key, data_type, lat_r, lon_r, source, payload_str, now),
                )
        except Exception:
            pass


def list_cached_types(db_path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    """Return count of cached records grouped by data_type."""
    with _LOCAL_LOCK:
        try:
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_type, COUNT(*) as cnt FROM geo_cache GROUP BY data_type"
            )
            return {row["data_type"]: row["cnt"] for row in cursor.fetchall()}
        except Exception:
            return {}
