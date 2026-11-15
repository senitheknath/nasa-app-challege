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

RESOLUTION_PRECISION: dict[str, int] = {
    "satellite_overpass": 1,
    "satellite_sensor": 1,
    "soil_grids": 2,
    "soil_wcs": 2,
    "terrain_dem": 3,
    "field_autofill": 3,
}


def resolve_precision(data_type: str, precision: int | None = None) -> int:
    """Resolve spatial grid rounding precision for a cache data_type unless explicitly overridden."""
    if precision is not None:
        return int(precision)
    dt = str(data_type or "")
    for prefix, prec in RESOLUTION_PRECISION.items():
        if dt.startswith(prefix):
            return prec
    return 3


def _resolve_db_path(db_path: Path | None) -> Path:
    return DEFAULT_DB_PATH if db_path is None else db_path


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return an initialized SQLite connection with foreign keys and WAL mode."""
    target_db = _resolve_db_path(db_path)
    target_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_db), timeout=10, check_same_thread=False)
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS provider_cache (
                request_key TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                payload_blob BLOB NOT NULL,
                retrieved_at TEXT NOT NULL,
                updated_at_epoch REAL NOT NULL
            )
            """
        )


def cell_key(data_type: str, latitude: float, longitude: float, precision: int | None = 3) -> str:
    """Format a cell key rounded to precision decimals (precision 3 ≈ 110 meters)."""
    eff_precision = resolve_precision(data_type, precision)
    lat_r = round(float(latitude), eff_precision) + 0.0
    lon_r = round(float(longitude), eff_precision) + 0.0
    return f"{data_type}:{lat_r:.{eff_precision}f}:{lon_r:.{eff_precision}f}"


def _parse_age_seconds(updated_at: str) -> float | None:
    try:
        dt = datetime.fromisoformat(str(updated_at))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None


def get_cached(
    data_type: str,
    latitude: float,
    longitude: float,
    *,
    precision: int | None = None,
    max_age_seconds: int | None = None,
    stale_while_revalidate_seconds: int | None = None,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Retrieve a cached record by cell key, or None if not found or outside SWR window."""
    eff_precision = resolve_precision(data_type, precision)
    key = cell_key(data_type, latitude, longitude, precision=eff_precision)
    with _LOCAL_LOCK:
        conn: sqlite3.Connection | None = None
        try:
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload_json, source, updated_at FROM geo_cache WHERE cell_key = ?",
                (key,),
            )
            row = cursor.fetchone()
            if row:
                is_stale = False
                if max_age_seconds is not None:
                    age_seconds = _parse_age_seconds(row["updated_at"])
                    if age_seconds is None:
                        return None
                    if age_seconds > max_age_seconds:
                        if (
                            stale_while_revalidate_seconds is not None
                            and age_seconds <= max_age_seconds + stale_while_revalidate_seconds
                        ):
                            is_stale = True
                        else:
                            return None
                data = json.loads(row["payload_json"])
                return {
                    "data": data,
                    "source": row["source"],
                    "updated_at": row["updated_at"],
                    "cached": True,
                    "is_stale": is_stale,
                }
        except Exception:
            return None
        finally:
            if conn is not None:
                conn.close()
    return None


def set_cached(
    data_type: str,
    latitude: float,
    longitude: float,
    payload: Any,
    *,
    source: str = "direct_api",
    precision: int | None = None,
    db_path: Path | None = None,
) -> None:
    """Store or update a payload into the spatial cache."""
    eff_precision = resolve_precision(data_type, precision)
    key = cell_key(data_type, latitude, longitude, precision=eff_precision)
    lat_r = round(float(latitude), eff_precision) + 0.0
    lon_r = round(float(longitude), eff_precision) + 0.0
    payload_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat()

    with _LOCAL_LOCK:
        conn: sqlite3.Connection | None = None
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
        finally:
            if conn is not None:
                conn.close()


def get_sensor_cached(
    sensor_id: str,
    latitude: float,
    longitude: float,
    *,
    max_age_seconds: int | None = 21600,
    stale_while_revalidate_seconds: int | None = None,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Retrieve a per-sensor cached payload at precision=1 (~11 km / 0.1 deg cell)."""
    return get_cached(
        f"satellite_sensor:{sensor_id}",
        latitude,
        longitude,
        precision=1,
        max_age_seconds=max_age_seconds,
        stale_while_revalidate_seconds=stale_while_revalidate_seconds,
        db_path=db_path,
    )


def set_sensor_cached(
    sensor_id: str,
    latitude: float,
    longitude: float,
    payload: Any,
    *,
    source: str = "satellite_api",
    db_path: Path | None = None,
) -> None:
    """Store a per-sensor payload at precision=1 (~11 km / 0.1 deg cell)."""
    set_cached(
        f"satellite_sensor:{sensor_id}",
        latitude,
        longitude,
        payload,
        source=source,
        precision=1,
        db_path=db_path,
    )


def list_cached_types(db_path: Path | None = None) -> dict[str, int]:
    """Return count of cached records grouped by data_type."""
    with _LOCAL_LOCK:
        conn: sqlite3.Connection | None = None
        try:
            conn = get_connection(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data_type, COUNT(*) as cnt FROM geo_cache GROUP BY data_type"
            )
            return {row["data_type"]: row["cnt"] for row in cursor.fetchall()}
        except Exception:
            return {}
        finally:
            if conn is not None:
                conn.close()


def get_provider_cached(
    request_key: str,
    *,
    max_age_seconds: int | None = 30 * 86400,
    db_path: Path = DEFAULT_DB_PATH,
) -> tuple[bytes, str] | None:
    """Return (raw_bytes, retrieved_at) from SQLite provider_cache, or None on miss/expiry."""
    import time

    with _LOCAL_LOCK:
        conn = None
        try:
            conn = get_connection(db_path)
            row = conn.execute(
                "SELECT payload_blob, retrieved_at, updated_at_epoch FROM provider_cache WHERE request_key = ?",
                (request_key,),
            ).fetchone()
            if not row:
                return None
            if max_age_seconds is not None and (time.time() - float(row["updated_at_epoch"])) > max_age_seconds:
                return None
            return bytes(row["payload_blob"]), str(row["retrieved_at"])
        except Exception:
            return None
        finally:
            if conn is not None:
                conn.close()


def set_provider_cached(
    request_key: str,
    url: str,
    payload: bytes,
    retrieved_at: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Persist a validated provider response into SQLite provider_cache."""
    import time

    with _LOCAL_LOCK:
        conn = None
        try:
            conn = get_connection(db_path)
            with conn:
                conn.execute(
                    """
                    INSERT INTO provider_cache (request_key, url, payload_blob, retrieved_at, updated_at_epoch)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(request_key) DO UPDATE SET
                        url = excluded.url,
                        payload_blob = excluded.payload_blob,
                        retrieved_at = excluded.retrieved_at,
                        updated_at_epoch = excluded.updated_at_epoch
                    """,
                    (request_key, url, bytes(payload), retrieved_at, time.time()),
                )
        except Exception:
            pass
        finally:
            if conn is not None:
                conn.close()
