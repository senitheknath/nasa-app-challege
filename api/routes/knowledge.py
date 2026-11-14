"""Unified 107-crop knowledge atlas and trait query routes."""
from __future__ import annotations

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from agroshift.knowledge import count_crops, crop_categories, knowledge_status, search_crops

from api.deps import json_response


async def crops_catalogue(request: Request) -> Response:
    """Search and paginate the 107-crop reviewed knowledge catalogue."""
    q = (request.query_params.get("q") or "").strip()
    category = (request.query_params.get("category") or "").strip() or None
    try:
        limit = int(request.query_params.get("limit", "50"))
        offset = int(request.query_params.get("offset", "0"))

        def _run():
            items = search_crops(query=q, limit=limit, offset=offset, category=category)
            total = count_crops(query=q, category=category)
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": items,
            }

        return json_response(await run_in_threadpool(_run))
    except ValueError as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def knowledge_categories_endpoint(_request: Request) -> Response:
    """Fetch all reviewed crop categories from the active knowledge database."""
    try:
        cats = await run_in_threadpool(crop_categories)
        return json_response({"categories": cats})
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=500)


async def knowledge_status_endpoint(_request: Request) -> Response:
    """Fetch versioning, backend, and metadata about the knowledge atlas."""
    try:
        def _run():
            info = knowledge_status()
            info["total_crops"] = count_crops()
            return info

        return json_response(await run_in_threadpool(_run))
    except Exception as exc:
        return json_response({"error": str(exc)}, status_code=500)


routes = [
    Route("/api/knowledge/crops", crops_catalogue, methods=["GET"]),
    Route("/api/knowledge/categories", knowledge_categories_endpoint, methods=["GET"]),
    Route("/api/knowledge/status", knowledge_status_endpoint, methods=["GET"]),
]
