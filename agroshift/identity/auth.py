"""Simple, robust SQLite-backed authentication and saved-farms repository for the backend."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import threading
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "users.db"
_AUTH_LOCK = threading.Lock()
_SALT = "agroshift_demo_salt_2026"


def _hash_password(password: str) -> str:
    """Deterministic salted hash for demo simplicity and speed."""
    return hashlib.sha256(f"{_SALT}:{password.strip()}".encode("utf-8")).hexdigest()


def get_auth_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return an initialized SQLite connection with foreign keys enabled."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                country TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                area_ha REAL,
                farm_json TEXT NOT NULL,
                boundary_json TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_token ON users(token)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_saved_farms_user ON saved_farms(user_id)")


def authenticate_or_register(
    email: str,
    password: str,
    display_name: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Authenticate existing user or automatically create account if new."""
    email_clean = email.strip().lower()
    if not email_clean or len(password.strip()) < 3:
        raise ValueError("Valid email/username and password (min 3 chars) required.")

    pwd_hash = _hash_password(password)
    now = datetime.now(timezone.utc).isoformat()

    with _AUTH_LOCK:
        conn = get_auth_connection(db_path)
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
            user_row = cursor.fetchone()

            if user_row:
                if user_row["password_hash"] != pwd_hash:
                    raise ValueError("Incorrect password.")
                token = user_row["token"]
                user = {
                    "id": user_row["id"],
                    "email": user_row["email"],
                    "display_name": user_row["display_name"],
                }
                return {"token": token, "user": user}

            # Register new user
            token = secrets.token_hex(24)
            name = (display_name or email_clean.split("@")[0]).strip()
            cursor.execute(
                """
                INSERT INTO users (email, display_name, password_hash, token, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (email_clean, name, pwd_hash, token, now),
            )
            user_id = cursor.lastrowid
            return {
                "token": token,
                "user": {"id": user_id, "email": email_clean, "display_name": name},
            }


def get_user_from_token(token: str | None, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Look up user profile by bearer token."""
    if not token or not isinstance(token, str):
        return None
    token_clean = token.replace("Bearer ", "").strip()
    with _AUTH_LOCK:
        try:
            conn = get_auth_connection(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, display_name FROM users WHERE token = ?", (token_clean,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        except Exception:
            return None
    return None


def list_user_farms(user_id: int, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """List all farms belonging to the authenticated user."""
    with _AUTH_LOCK:
        conn = get_auth_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, country, latitude, longitude, area_ha, farm_json, boundary_json, updated_at
            FROM saved_farms WHERE user_id = ? ORDER BY updated_at DESC
            """,
            (user_id,),
        )
        farms = []
        for r in cursor.fetchall():
            farms.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "country": r["country"],
                    "latitude": r["latitude"],
                    "longitude": r["longitude"],
                    "area_ha": r["area_ha"],
                    "farm": json.loads(r["farm_json"]),
                    "boundary": json.loads(r["boundary_json"]) if r["boundary_json"] else None,
                    "updated_at": r["updated_at"],
                }
            )
        return farms


def save_user_farm(
    user_id: int,
    name: str,
    farm_data: dict[str, Any],
    boundary_data: dict[str, Any] | None = None,
    farm_id: int | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Save a new farm or update an existing farm."""
    name_clean = str(name).strip() or "Untitled Field"
    country = str(farm_data.get("country", "LK")).upper()
    lat = float(farm_data.get("latitude", 0.0))
    lon = float(farm_data.get("longitude", 0.0))
    area_ha = float(farm_data["area_ha"]) if farm_data.get("area_ha") is not None else None
    farm_str = json.dumps(farm_data, separators=(",", ":"))
    boundary_str = json.dumps(boundary_data, separators=(",", ":")) if boundary_data else None
    now = datetime.now(timezone.utc).isoformat()

    with _AUTH_LOCK:
        conn = get_auth_connection(db_path)
        with conn:
            cursor = conn.cursor()
            if farm_id is not None:
                cursor.execute(
                    """
                    UPDATE saved_farms
                    SET name = ?, country = ?, latitude = ?, longitude = ?, area_ha = ?,
                        farm_json = ?, boundary_json = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (name_clean, country, lat, lon, area_ha, farm_str, boundary_str, now, farm_id, user_id),
                )
                if cursor.rowcount == 0:
                    raise ValueError("Farm not found or not owned by user.")
                saved_id = farm_id
            else:
                cursor.execute(
                    """
                    INSERT INTO saved_farms (user_id, name, country, latitude, longitude, area_ha, farm_json, boundary_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, name_clean, country, lat, lon, area_ha, farm_str, boundary_str, now),
                )
                saved_id = cursor.lastrowid

            return {
                "id": saved_id,
                "name": name_clean,
                "country": country,
                "latitude": lat,
                "longitude": lon,
                "area_ha": area_ha,
                "updated_at": now,
            }


def delete_user_farm(user_id: int, farm_id: int, db_path: Path = DEFAULT_DB_PATH) -> bool:
    """Delete a farm owned by the user."""
    with _AUTH_LOCK:
        conn = get_auth_connection(db_path)
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_farms WHERE id = ? AND user_id = ?", (farm_id, user_id))
            return cursor.rowcount > 0
