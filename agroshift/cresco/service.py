"""High-level Cresco AI service orchestrating session, context, prompt, and Gemini."""
from __future__ import annotations

from typing import Any, Callable

import httpx

from agroshift.cresco.context_builder import build_agricultural_context
from agroshift.cresco.gemini_client import (
    DEFAULT_GEMINI_MODEL,
    GeminiError,
    generate_chat_reply,
    verify_api_key,
)
from agroshift.cresco.prompt_builder import build_system_instruction
from agroshift.cresco.session_store import DEFAULT_SESSION_STORE, CrescoSessionStore


class CrescoService:
    """Service layer for Cresco AI connect, status, chat, clear, and disconnect."""

    def __init__(
        self,
        *,
        session_store: CrescoSessionStore = DEFAULT_SESSION_STORE,
        model: str = DEFAULT_GEMINI_MODEL,
        transport: httpx.AsyncBaseTransport | None = None,
        dataset_loader: Callable[[float, float], Any] | None = None,
    ) -> None:
        self.session_store = session_store
        self.model = model
        self.transport = transport
        self.dataset_loader = dataset_loader

    async def connect(
        self,
        *,
        api_key: str,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Verify the Gemini API key live and create an isolated in-memory session."""
        await verify_api_key(
            api_key,
            model=self.model,
            transport=self.transport,
        )
        session = self.session_store.create_session(
            api_key.strip(),
            user_id=user_id,
            model=self.model,
        )
        return {
            "connected": True,
            "model": session.model,
            "session_token": session.session_id,
            "expires_at": session.expires_at_iso(),
            "ttl_seconds": session.ttl_remaining(self.session_store.now()),
        }

    def status(
        self,
        *,
        session_id: str | None,
        user_id: int | None = None,
        farm_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Return connection status and farm-scoped history for the active session."""
        session = self.session_store.get_session(session_id, user_id=user_id)
        if session is None:
            return {
                "connected": False,
                "model": self.model,
                "expires_at": None,
                "ttl_seconds": 0,
                "history_count": 0,
                "history": [],
            }
        raw_history = self.session_store.get_history(
            session.session_id,
            farm_id,
            user_id=user_id,
        )
        ui_history = [
            {
                "role": "assistant" if turn.get("role") == "model" else "user",
                "content": turn.get("text", ""),
            }
            for turn in raw_history
        ]
        return {
            "connected": True,
            "model": session.model,
            "expires_at": session.expires_at_iso(),
            "ttl_seconds": session.ttl_remaining(self.session_store.now()),
            "history_count": len(ui_history),
            "history": ui_history,
        }

    async def chat(
        self,
        *,
        session_id: str | None,
        user_id: int | None = None,
        message: str,
        farm_id: str | int | None = None,
        inline_farm: dict[str, Any] | None = None,
        season: str | None = None,
        area_id: str | None = None,
        language: str | None = None,
        clear_history: bool = False,
    ) -> dict[str, Any]:
        """Ground a user message in farm context and call Gemini."""
        session = self.session_store.get_session(session_id, user_id=user_id)
        if session is None:
            raise GeminiError(
                error_code="session_not_connected",
                status_code=401,
                message="Cresco AI is not connected. Please verify a Gemini API key first.",
            )

        clean_msg = str(message or "").strip()
        if not clean_msg:
            raise GeminiError(
                error_code="empty_message",
                status_code=400,
                message="Message must not be empty.",
            )

        if clear_history:
            self.session_store.clear_history(
                session.session_id,
                farm_id,
                user_id=user_id,
            )

        context = build_agricultural_context(
            user_id=user_id,
            farm_id=farm_id,
            inline_farm=inline_farm,
            season=season,
            area_id=area_id,
            user_message=clean_msg,
            dataset_loader=self.dataset_loader,
        )
        system_instruction, lang_code = build_system_instruction(
            context,
            language=language,
            user_message=clean_msg,
        )
        history = self.session_store.get_history(
            session.session_id,
            farm_id,
            user_id=user_id,
        )

        reply = await generate_chat_reply(
            session.api_key,
            system_instruction=system_instruction,
            history=history,
            user_message=clean_msg,
            model=session.model,
            transport=self.transport,
        )

        history_count = self.session_store.append_turn(
            session.session_id,
            farm_id,
            clean_msg,
            reply,
            user_id=user_id,
        )

        return {
            "reply": reply,
            "model": session.model,
            "farm_id": str(farm_id) if farm_id is not None else None,
            "language": lang_code,
            "provenance_summary": context["provenance_summary"],
            "history_count": history_count,
        }

    def clear(
        self,
        *,
        session_id: str | None,
        user_id: int | None = None,
        farm_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Clear conversation history for the given farm or whole session."""
        session = self.session_store.get_session(session_id, user_id=user_id)
        if session is None:
            raise GeminiError(
                error_code="session_not_connected",
                status_code=401,
                message="Cresco AI is not connected.",
            )
        self.session_store.clear_history(
            session.session_id,
            farm_id,
            user_id=user_id,
        )
        return {
            "cleared": True,
            "farm_id": str(farm_id) if farm_id is not None else None,
        }

    def disconnect(
        self,
        *,
        session_id: str | None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Delete the session and purge the API key from server memory."""
        self.session_store.delete_session(session_id, user_id=user_id)
        return {"connected": False, "disconnected": True}
