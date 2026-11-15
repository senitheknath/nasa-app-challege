"""Cresco AI Gemini-backed agricultural assistant routes."""
from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from agroshift.cresco.gemini_client import GeminiError
from agroshift.cresco.service import CrescoService
from api.deps import get_dataset, get_optional_auth_user, json_response

CRESCO_COOKIE_NAME = "cresco_session"
CRESCO_HEADER_NAME = "X-Cresco-Session"

DEFAULT_CRESCO_SERVICE = CrescoService(dataset_loader=get_dataset)


def _extract_user_id(request: Request) -> int | None:
    user = get_optional_auth_user(request)
    return int(user["id"]) if user and user.get("id") is not None else None


def _extract_session_id(request: Request) -> str | None:
    header_val = (request.headers.get(CRESCO_HEADER_NAME) or "").strip()
    if header_val:
        return header_val
    cookie_val = (request.cookies.get(CRESCO_COOKIE_NAME) or "").strip()
    return cookie_val or None


async def _read_json_body(request: Request) -> dict[str, Any]:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


async def cresco_connect(request: Request) -> Response:
    """Verify a user-supplied Gemini API key live and open an isolated Cresco session."""
    payload = await _read_json_body(request)
    api_key = str(payload.get("api_key") or "")
    user_id = _extract_user_id(request)
    try:
        res = await DEFAULT_CRESCO_SERVICE.connect(api_key=api_key, user_id=user_id)
        response = json_response(res, status_code=200)
        response.set_cookie(
            key=CRESCO_COOKIE_NAME,
            value=res["session_token"],
            max_age=int(res["ttl_seconds"]),
            httponly=True,
            samesite="lax",
        )
        return response
    except GeminiError as exc:
        return json_response(
            {"connected": False, "error": exc.message, "error_code": exc.error_code},
            status_code=exc.status_code,
        )
    except Exception:
        return json_response(
            {
                "connected": False,
                "error": "Failed to verify Gemini API key.",
                "error_code": "upstream_error",
            },
            status_code=502,
        )


async def cresco_status(request: Request) -> Response:
    """Return active Cresco connection status and farm-scoped history."""
    session_id = _extract_session_id(request)
    user_id = _extract_user_id(request)
    farm_id = request.query_params.get("farm_id")
    res = DEFAULT_CRESCO_SERVICE.status(
        session_id=session_id,
        user_id=user_id,
        farm_id=farm_id,
    )
    return json_response(res, status_code=200)


async def cresco_chat(request: Request) -> Response:
    """Send a farm-grounded message to Gemini 3.8 Flash within the active session."""
    payload = await _read_json_body(request)
    session_id = _extract_session_id(request)
    user_id = _extract_user_id(request)
    try:
        res = await DEFAULT_CRESCO_SERVICE.chat(
            session_id=session_id,
            user_id=user_id,
            message=str(payload.get("message") or ""),
            farm_id=payload.get("farm_id"),
            inline_farm=payload.get("farm") if isinstance(payload.get("farm"), dict) else None,
            season=payload.get("season"),
            area_id=payload.get("area_id"),
            language=payload.get("language"),
            clear_history=bool(payload.get("clear_history", False)),
        )
        return json_response(res, status_code=200)
    except GeminiError as exc:
        return json_response(
            {"error": exc.message, "error_code": exc.error_code},
            status_code=exc.status_code,
        )
    except Exception as exc:
        return json_response(
            {"error": f"Cresco chat failed: {exc}", "error_code": "internal_error"},
            status_code=500,
        )


async def cresco_clear(request: Request) -> Response:
    """Clear farm-scoped (or all) conversation history for the active session."""
    payload = await _read_json_body(request)
    session_id = _extract_session_id(request)
    user_id = _extract_user_id(request)
    try:
        res = DEFAULT_CRESCO_SERVICE.clear(
            session_id=session_id,
            user_id=user_id,
            farm_id=payload.get("farm_id"),
        )
        return json_response(res, status_code=200)
    except GeminiError as exc:
        return json_response(
            {"error": exc.message, "error_code": exc.error_code},
            status_code=exc.status_code,
        )


async def cresco_disconnect(request: Request) -> Response:
    """Delete the active Cresco session and purge the API key from memory."""
    session_id = _extract_session_id(request)
    user_id = _extract_user_id(request)
    res = DEFAULT_CRESCO_SERVICE.disconnect(session_id=session_id, user_id=user_id)
    response = json_response(res, status_code=200)
    response.delete_cookie(CRESCO_COOKIE_NAME)
    return response


routes = [
    Route("/api/cresco/connect", cresco_connect, methods=["POST"]),
    Route("/api/cresco/status", cresco_status, methods=["GET"]),
    Route("/api/cresco/chat", cresco_chat, methods=["POST"]),
    Route("/api/cresco/clear", cresco_clear, methods=["POST"]),
    Route("/api/cresco/disconnect", cresco_disconnect, methods=["POST"]),
]
