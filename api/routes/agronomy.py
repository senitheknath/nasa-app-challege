"""Agronomic crop screening, deep evidence, multi-season DAG rotations, and reporting routes."""
from __future__ import annotations

from dataclasses import asdict

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Route

from agroshift.climate_insights import (
    crop_12month_sowing_matrix,
    crop_stage_water_demand,
    previous_crop_rotation_badge,
    seasonal_weather_risk_summary,
)
from agroshift.evidence_combination import build_evidence_layers
from agroshift.farm_context import capabilities, location_context
from agroshift.finder_report import make_record, readable
from agroshift.knowledge import crop_by_id, global_traits
from agroshift.pests import evaluate_crop_pest_context
from agroshift.power import DataError
from agroshift.providers import GAEZ_CROP_ID_MAP, gaez_point, gaez_polygon
from agroshift.rotation import plan_global_rotations
from agroshift.screening import find_options
from agroshift.water_balance import seasonal_water_balance_summary

from api.deps import get_dataset, json_response, parse_weights, resolve_farm


async def screen(request: Request) -> Response:
    """Screen all 107 crops for a farm's climate, soil, and seasonal windows."""
    try:
        payload = await request.json()
        farm = resolve_farm(request, payload)
        weights = parse_weights(payload.get("weights"))
        include_matrix = bool(payload.get("include_sowing_matrix", True))

        def _run():
            ds = get_dataset(farm.latitude, farm.longitude)
            cards = find_options(farm, ds, weights=weights)
            risk = seasonal_weather_risk_summary(ds, farm.windows[0])
            caps = capabilities(farm, ds, cards)
            matrix = crop_12month_sowing_matrix(ds, cards) if include_matrix else None
            return {
                "farm": asdict(farm),
                "capabilities": caps,
                "weather_risk": risk,
                "sowing_matrix": matrix,
                "cards": cards,
            }

        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def crop_details(request: Request) -> Response:
    """Retrieve deep agronomic evidence, water demand, GAEZ suitability, and pest context for one crop."""
    crop_id = request.path_params["crop_id"]
    try:
        payload = await request.json()
        farm = resolve_farm(request, payload)
        weights = parse_weights(payload.get("weights"))
        offline = bool(payload.get("offline", False))
        boundary = payload.get("boundary")

        def _run():
            ds = get_dataset(farm.latitude, farm.longitude)
            cards = find_options(farm, ds, weights=weights)
            card = next((c for c in cards if c.get("id") == crop_id), None)
            if card is None:
                raise ValueError(f"Crop '{crop_id}' not found in screening cards.")

            crop_identity = crop_by_id(crop_id)
            layers = build_evidence_layers(card, ds, farm)
            water_stages = crop_stage_water_demand(ds, farm.windows[0], crop_id)
            water_balance = seasonal_water_balance_summary(ds, farm.windows[0], crop_id, farm)
            extremes = ds.extremes if hasattr(ds, "extremes") else {}

            gaez_name = GAEZ_CROP_ID_MAP.get(crop_id)
            gaez_rainfed = None
            gaez_irrigated = None
            if gaez_name:
                if boundary and isinstance(boundary, dict):
                    gaez_rainfed = gaez_polygon(
                        boundary, crop=gaez_name, water="rainfed", offline=offline
                    )
                    gaez_irrigated = gaez_polygon(
                        boundary, crop=gaez_name, water="irrigated", offline=offline
                    )
                else:
                    gaez_rainfed = gaez_point(
                        farm.latitude, farm.longitude, crop=gaez_name, water="rainfed", offline=offline
                    )
                    gaez_irrigated = gaez_point(
                        farm.latitude, farm.longitude, crop=gaez_name, water="irrigated", offline=offline
                    )

            pest_ctx = evaluate_crop_pest_context(crop_id, ds, farm.windows[0])
            rot_badge = previous_crop_rotation_badge(farm.previous, crop_id)
            traits = global_traits(crop_id)

            return {
                "card": card,
                "crop": crop_identity,
                "evidence_layers": layers,
                "water_stages": water_stages,
                "water_balance": water_balance,
                "extremes": extremes,
                "gaez": {
                    "mapped_crop": gaez_name,
                    "rainfed": gaez_rainfed,
                    "irrigated": gaez_irrigated,
                },
                "pest_context": pest_ctx,
                "rotation_badge": rot_badge,
                "traits": traits,
            }

        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def rotations(request: Request) -> Response:
    """Plan and rate multi-season crop rotations with classical interval DAG physical timelines."""
    try:
        payload = await request.json()
        farm = resolve_farm(request, payload)
        max_sequences = int(payload.get("max_sequences", 16))

        def _run():
            ds = get_dataset(farm.latitude, farm.longitude)
            plans = plan_global_rotations(farm, ds, max_sequences=max_sequences)
            return {
                "status": "success",
                "total": len(plans),
                "rotations": plans,
            }

        return json_response(await run_in_threadpool(_run))
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def report(request: Request) -> Response:
    """Generate a full JSON or HTML agronomic decision report."""
    fmt = (request.query_params.get("format") or "json").lower()
    try:
        payload = await request.json()
        farm = resolve_farm(request, payload)
        weights = parse_weights(payload.get("weights"))
        offline = bool(payload.get("offline", False))

        def _run():
            ds = get_dataset(farm.latitude, farm.longitude)
            cards = find_options(farm, ds, weights=weights)
            ctx = location_context(farm.country, farm.latitude, farm.longitude, offline=offline)
            record = make_record(ds, farm, cards, weights, context=ctx)
            if fmt == "html":
                return readable(record)
            return record

        result = await run_in_threadpool(_run)
        if fmt == "html":
            return HTMLResponse(result)
        return json_response(result)
    except (DataError, ValueError, KeyError, TypeError) as exc:
        return json_response({"error": str(exc)}, status_code=400)


routes = [
    Route("/api/agronomy/screen", screen, methods=["POST"]),
    Route("/api/agronomy/crops/{crop_id}/details", crop_details, methods=["POST"]),
    Route("/api/agronomy/rotations", rotations, methods=["POST"]),
    Route("/api/agronomy/report", report, methods=["POST"]),
]
