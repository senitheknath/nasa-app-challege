"""Cresco AI agricultural assistant package for AgroShift."""
from __future__ import annotations

from agroshift.cresco.context_builder import build_agricultural_context
from agroshift.cresco.gemini_client import (
    DEFAULT_GEMINI_MODEL,
    GeminiError,
    generate_chat_reply,
    verify_api_key,
)
from agroshift.cresco.prompt_builder import build_system_instruction, resolve_response_language
from agroshift.cresco.service import CrescoService
from agroshift.cresco.session_store import DEFAULT_SESSION_STORE, CrescoSession, CrescoSessionStore

__all__ = [
    "CrescoService",
    "CrescoSession",
    "CrescoSessionStore",
    "DEFAULT_GEMINI_MODEL",
    "DEFAULT_SESSION_STORE",
    "GeminiError",
    "build_agricultural_context",
    "build_system_instruction",
    "generate_chat_reply",
    "resolve_response_language",
    "verify_api_key",
]
