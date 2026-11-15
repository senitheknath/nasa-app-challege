"""Async Gemini REST client for Cresco AI using httpx (model: gemini-flash-lite-latest)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


@dataclass
class GeminiError(Exception):
    """Structured error raised by Gemini API calls without ever exposing the API key."""

    error_code: str
    status_code: int
    message: str

    def __str__(self) -> str:
        return self.message


def _extract_google_error_info(response: httpx.Response) -> tuple[str, str]:
    """Safely extract Google API error status and message without leaking secrets."""
    try:
        data = response.json()
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict):
            status = str(err.get("status") or "").upper()
            message = str(err.get("message") or "").strip()
            details = err.get("details") or []
            for item in details:
                if isinstance(item, dict) and item.get("reason"):
                    status = f"{status} {str(item['reason']).upper()}".strip()
            return status, message
    except Exception:
        pass
    return "", ""


def _map_http_error(response: httpx.Response, model: str) -> GeminiError:
    """Map Gemini HTTP error status and Google error codes to structured GeminiError."""
    code = response.status_code
    g_status, g_msg = _extract_google_error_info(response)
    combined = f"{g_status} {g_msg}".upper()

    if (
        code in (401, 403)
        or "API_KEY_INVALID" in combined
        or "UNAUTHENTICATED" in combined
        or "PERMISSION_DENIED" in combined
        or "API KEY NOT VALID" in combined
    ):
        return GeminiError(
            error_code="invalid_api_key",
            status_code=401,
            message="Invalid or unauthorized Gemini API key.",
        )
    if code == 404 or "NOT_FOUND" in combined:
        return GeminiError(
            error_code="model_unavailable",
            status_code=404,
            message=f"Gemini model '{model}' is unavailable for this API key.",
        )
    if code == 429 or "RESOURCE_EXHAUSTED" in combined or "QUOTA" in combined:
        return GeminiError(
            error_code="quota_exceeded",
            status_code=429,
            message="Gemini API quota or rate limit exceeded.",
        )
    if code == 400:
        detail = g_msg or "Invalid request sent to Gemini API."
        return GeminiError(
            error_code="invalid_request",
            status_code=400,
            message=detail,
        )
    if code == 503 or "UNAVAILABLE" in combined:
        return GeminiError(
            error_code="upstream_error",
            status_code=503,
            message="Gemini API is temporarily overloaded (503). Please try again in a moment.",
        )
    return GeminiError(
        error_code="upstream_error",
        status_code=502,
        message=f"Gemini API returned unexpected status {code}.",
    )


def _endpoint_url(model: str) -> str:
    clean_model = str(model or DEFAULT_GEMINI_MODEL).strip()
    return f"{GEMINI_API_BASE}/{clean_model}:generateContent"


async def verify_api_key(
    api_key: str,
    *,
    model: str = DEFAULT_GEMINI_MODEL,
    timeout: float = 30.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """Verify a Gemini API key by making a real authenticated generateContent call.

    Never accepts a key based on format alone and never retries billable requests.
    """
    clean_key = str(api_key or "").strip()
    if not clean_key:
        raise GeminiError(
            error_code="missing_api_key",
            status_code=400,
            message="Gemini API key is required.",
        )

    url = _endpoint_url(model)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "Reply with ok."}]}],
        "generationConfig": {"maxOutputTokens": 4, "temperature": 0.0},
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": clean_key,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise GeminiError(
            error_code="timeout",
            status_code=504,
            message="Timed out while verifying Gemini API key.",
        ) from exc
    except httpx.RequestError as exc:
        raise GeminiError(
            error_code="network_error",
            status_code=502,
            message="Network error while contacting Gemini API.",
        ) from exc

    if response.status_code != 200:
        raise _map_http_error(response, model)

    return {"verified": True, "model": model}


async def generate_chat_reply(
    api_key: str,
    *,
    system_instruction: str,
    history: list[dict[str, str]],
    user_message: str,
    model: str = DEFAULT_GEMINI_MODEL,
    timeout: float = 45.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    """Send a grounded chat turn to Gemini generateContent and return the model reply."""
    clean_key = str(api_key or "").strip()
    if not clean_key:
        raise GeminiError(
            error_code="invalid_api_key",
            status_code=401,
            message="Gemini API session is missing a valid key.",
        )

    contents: list[dict[str, Any]] = []
    for turn in history:
        role = "model" if turn.get("role") in ("model", "assistant") else "user"
        text = str(turn.get("text") or turn.get("content") or "").strip()
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2048,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": clean_key,
    }
    url = _endpoint_url(model)

    try:
        async with httpx.AsyncClient(timeout=timeout, transport=transport) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise GeminiError(
            error_code="timeout",
            status_code=504,
            message="Timed out while waiting for Gemini response.",
        ) from exc
    except httpx.RequestError as exc:
        raise GeminiError(
            error_code="network_error",
            status_code=502,
            message="Network error while contacting Gemini API.",
        ) from exc

    if response.status_code != 200:
        raise _map_http_error(response, model)

    try:
        data = response.json()
    except Exception as exc:
        raise GeminiError(
            error_code="upstream_error",
            status_code=502,
            message="Gemini API returned invalid JSON.",
        ) from exc

    candidates = data.get("candidates") if isinstance(data, dict) else None
    if not candidates or not isinstance(candidates, list):
        prompt_fb = data.get("promptFeedback") if isinstance(data, dict) else None
        if isinstance(prompt_fb, dict) and prompt_fb.get("blockReason"):
            raise GeminiError(
                error_code="content_blocked",
                status_code=400,
                message="Request was blocked by Gemini safety filters.",
            )
        raise GeminiError(
            error_code="empty_response",
            status_code=502,
            message="Gemini API returned no response candidates.",
        )

    parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
    texts = [str(p.get("text")) for p in parts if isinstance(p, dict) and p.get("text")]
    reply = "\n".join(texts).strip()
    if not reply:
        raise GeminiError(
            error_code="empty_response",
            status_code=502,
            message="Gemini API returned an empty text response.",
        )
    return reply
