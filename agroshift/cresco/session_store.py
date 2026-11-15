"""In-memory, TTL-backed, per-session isolated store for Cresco AI."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
import secrets
import threading
import time
from typing import Callable


DEFAULT_TTL_SECONDS = int(os.getenv("CRESCO_SESSION_TTL_SECONDS", "3600") or "3600")
DEFAULT_MAX_HISTORY_MESSAGES = 24
DEFAULT_MODEL = "gemini-flash-lite-latest"


def _normalize_farm_key(farm_id: str | int | None) -> str:
    """Normalize farm identifier into a deterministic history scope key."""
    if farm_id is None:
        return "default"
    text = str(farm_id).strip()
    return text if text else "default"


@dataclass
class CrescoSession:
    """Ephemeral in-memory Cresco session holding a verified Gemini key."""

    session_id: str
    api_key: str = field(repr=False)
    user_id: int | None
    model: str
    created_at: float
    expires_at: float
    histories: dict[str, list[dict[str, str]]] = field(default_factory=dict, repr=False)

    def expires_at_iso(self) -> str:
        return datetime.fromtimestamp(self.expires_at, tz=timezone.utc).isoformat()

    def ttl_remaining(self, now: float) -> int:
        return max(0, int(round(self.expires_at - now)))

    def history_count(self, farm_id: str | int | None = None) -> int:
        key = _normalize_farm_key(farm_id)
        return len(self.histories.get(key, []))

    def clear_sensitive_data(self) -> None:
        """Overwrite sensitive in-memory references on disconnect/expiry."""
        self.api_key = ""
        self.histories.clear()


class CrescoSessionStore:
    """Thread-safe, in-memory TTL store isolating Gemini keys and farm-scoped chats."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_history_messages: int = DEFAULT_MAX_HISTORY_MESSAGES,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._ttl_seconds = max(60, int(ttl_seconds))
        self._max_history_messages = max(2, int(max_history_messages))
        self._clock = clock
        self._lock = threading.RLock()
        self._sessions: dict[str, CrescoSession] = {}

    def purge_expired(self) -> int:
        """Delete all expired sessions and clear their in-memory API keys."""
        now = self._clock()
        removed = 0
        with self._lock:
            expired_ids = [
                sid for sid, sess in self._sessions.items() if sess.expires_at <= now
            ]
            for sid in expired_ids:
                sess = self._sessions.pop(sid, None)
                if sess is not None:
                    sess.clear_sensitive_data()
                    removed += 1
        return removed

    def create_session(
        self,
        api_key: str,
        *,
        user_id: int | None = None,
        model: str = DEFAULT_MODEL,
    ) -> CrescoSession:
        """Create a new isolated session for a verified Gemini API key."""
        now = self._clock()
        self.purge_expired()
        session_id = secrets.token_urlsafe(32)
        session = CrescoSession(
            session_id=session_id,
            api_key=api_key,
            user_id=user_id,
            model=model,
            created_at=now,
            expires_at=now + self._ttl_seconds,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_session(
        self,
        session_id: str | None,
        *,
        user_id: int | None = None,
    ) -> CrescoSession | None:
        """Retrieve an active session if valid, unexpired, and owned by the caller."""
        if not session_id or not str(session_id).strip():
            return None
        sid = str(session_id).strip()
        now = self._clock()
        with self._lock:
            sess = self._sessions.get(sid)
            if sess is None:
                return None
            if sess.expires_at <= now:
                self._sessions.pop(sid, None)
                sess.clear_sensitive_data()
                return None
            if sess.user_id is not None and user_id != sess.user_id:
                return None
            return sess

    def get_history(
        self,
        session_id: str | None,
        farm_id: str | int | None = None,
        *,
        user_id: int | None = None,
    ) -> list[dict[str, str]]:
        """Return a copy of the conversation history for (session_id, farm_id)."""
        with self._lock:
            sess = self.get_session(session_id, user_id=user_id)
            if sess is None:
                return []
            key = _normalize_farm_key(farm_id)
            return [dict(turn) for turn in sess.histories.get(key, [])]

    def append_turn(
        self,
        session_id: str,
        farm_id: str | int | None,
        user_message: str,
        assistant_reply: str,
        *,
        user_id: int | None = None,
    ) -> int:
        """Append a user/model exchange to the farm-scoped history and return count."""
        with self._lock:
            sess = self.get_session(session_id, user_id=user_id)
            if sess is None:
                return 0
            key = _normalize_farm_key(farm_id)
            history = sess.histories.setdefault(key, [])
            history.append({"role": "user", "text": user_message})
            history.append({"role": "model", "text": assistant_reply})
            if len(history) > self._max_history_messages:
                del history[: len(history) - self._max_history_messages]
            return len(history)

    def clear_history(
        self,
        session_id: str | None,
        farm_id: str | int | None = None,
        *,
        user_id: int | None = None,
    ) -> bool:
        """Clear conversation history for one farm or all farms in a session."""
        with self._lock:
            sess = self.get_session(session_id, user_id=user_id)
            if sess is None:
                return False
            if farm_id is None:
                sess.histories.clear()
            else:
                sess.histories.pop(_normalize_farm_key(farm_id), None)
            return True

    def delete_session(
        self,
        session_id: str | None,
        *,
        user_id: int | None = None,
    ) -> bool:
        """Delete a session and immediately purge its API key from memory."""
        if not session_id or not str(session_id).strip():
            return False
        sid = str(session_id).strip()
        with self._lock:
            sess = self._sessions.get(sid)
            if sess is None:
                return False
            if sess.user_id is not None and user_id != sess.user_id:
                return False
            self._sessions.pop(sid, None)
            sess.clear_sensitive_data()
            return True

    def now(self) -> float:
        return self._clock()


DEFAULT_SESSION_STORE = CrescoSessionStore()
