"""Optional user authentication and saved multi-farm persistence routes."""
from __future__ import annotations

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from agroshift.identity import (
    authenticate_or_register,
    delete_user_farm,
    list_user_farms,
    save_user_farm,
)

from api.deps import get_required_auth_user, json_response


async def auth_login(request: Request) -> Response:
    """Authenticate or register an optional user account to persist saved farms."""
    try:
        payload = await request.json()
        email = str(payload.get("email") or payload.get("username") or "")
        password = str(payload.get("password") or "")
        display_name = payload.get("display_name")
        res = await run_in_threadpool(authenticate_or_register, email, password, display_name)
        return json_response(res)
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def auth_me(request: Request) -> Response:
    """Return the currently authenticated user profile."""
    try:
        user = get_required_auth_user(request)
        return json_response({"user": user})
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=401)


async def farms_list(request: Request) -> Response:
    """List all saved farms for the authenticated user."""
    try:
        user = get_required_auth_user(request)
        farms = await run_in_threadpool(list_user_farms, user["id"])
        return json_response({"farms": farms})
    except ValueError as exc:
        return json_response({"error": str(exc)}, status_code=401)
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def farms_get(request: Request) -> Response:
    """Retrieve a single saved farm by ID for the authenticated user."""
    try:
        user = get_required_auth_user(request)
        farm_id = int(request.path_params["farm_id"])
        farms = await run_in_threadpool(list_user_farms, user["id"])
        farm = next((f for f in farms if f["id"] == farm_id), None)
        if not farm:
            return json_response({"error": "Farm not found"}, status_code=404)
        return json_response({"farm": farm})
    except ValueError as exc:
        return json_response({"error": str(exc)}, status_code=401)
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def farms_save(request: Request) -> Response:
    """Create or update a saved farm (with boundary and telemetry) for the authenticated user."""
    try:
        user = get_required_auth_user(request)
        payload = await request.json()
        name = str(payload.get("name") or "My Farm")
        farm_data = payload.get("farm") or payload
        boundary = payload.get("boundary")
        farm_id = payload.get("id")
        if "farm_id" in request.path_params:
            farm_id = int(request.path_params["farm_id"])
        saved = await run_in_threadpool(
            save_user_farm, user["id"], name, farm_data, boundary, farm_id
        )
        return json_response({"farm": saved, "status": "saved"})
    except ValueError as exc:
        status_code = 401 if "Unauthorized" in str(exc) else 400
        return json_response({"error": str(exc)}, status_code=status_code)
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def farms_delete(request: Request) -> Response:
    """Delete a saved farm for the authenticated user."""
    try:
        user = get_required_auth_user(request)
        farm_id = int(request.path_params["farm_id"])
        ok = await run_in_threadpool(delete_user_farm, user["id"], farm_id)
        if not ok:
            return json_response({"error": "Farm not found"}, status_code=404)
        return json_response({"status": "deleted", "id": farm_id})
    except ValueError as exc:
        status_code = 401 if "Unauthorized" in str(exc) else 400
        return json_response({"error": str(exc)}, status_code=status_code)
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=400)


routes = [
    Route("/api/auth/login", auth_login, methods=["POST"]),
    Route("/api/auth/register", auth_login, methods=["POST"]),
    Route("/api/auth/me", auth_me, methods=["GET"]),
    Route("/api/farms", farms_list, methods=["GET"]),
    Route("/api/farms", farms_save, methods=["POST"]),
    Route("/api/farms/{farm_id:int}", farms_get, methods=["GET"]),
    Route("/api/farms/{farm_id:int}", farms_save, methods=["PUT"]),
    Route("/api/farms/{farm_id:int}", farms_delete, methods=["DELETE"]),
]
