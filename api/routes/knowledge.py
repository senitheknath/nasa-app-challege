"""Unified 107-crop knowledge atlas and trait query routes."""
from __future__ import annotations

from collections import defaultdict

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from agroshift.earth_data.locations import country_regions
from agroshift.knowledge import count_crops, crop_categories, global_traits, knowledge_status, search_crops
from agroshift.power import DataError
from agroshift.science.decision.screening import find_options
from agroshift.science.knowledge.knowledge import screening_candidates

from api.deps import get_dataset, json_response, parse_farm

# FAO reference yield (t/ha) for the reviewed agronomic rotation crops
_FAO_REFERENCE_YIELD_THA: dict[str, float] = {
    "barley": 3.2,
    "faba_bean": 2.4,
    "cabbage": 24.0,
    "carrot": 22.0,
    "cassava": 14.5,
    "chickpea": 1.6,
    "common_bean": 1.8,
    "cotton": 2.6,
    "cowpea": 1.5,
    "dry_pea": 2.3,
    "eggplant": 20.5,
    "groundnut": 2.2,
    "lentil": 1.4,
    "maize": 5.8,
    "mung_bean": 1.2,
    "oat": 2.9,
    "oats": 2.9,
    "onion": 19.5,
    "pearl_millet": 1.9,
    "potato": 21.5,
    "rapeseed": 2.4,
    "rice": 4.8,
    "sesame": 1.1,
    "sorghum": 3.1,
    "soybean": 2.8,
    "sugar_beet": 48.0,
    "sugarcane": 65.0,
    "sunflower": 2.1,
    "sweet_potato": 13.0,
    "tomato": 28.0,
    "wheat": 3.6,
}


def _build_crop_enrichment() -> tuple[set[str], dict[str, dict]]:
    by_crop: dict[str, dict] = defaultdict(dict)
    for t in global_traits():
        if t.get("review_status") == "reviewed" and t.get("scope") == "global":
            by_crop[t["crop_id"]][t["trait"]] = t
    supported_ids = {c["id"] for c in screening_candidates(by_crop) if c["id"] != "oat"}
    return supported_ids, by_crop


def _enrich_crop_item(item: dict, traits: dict, card: dict | None = None) -> dict:
    cid = item["id"]
    et = traits.get("seasonal_crop_et")
    kc = traits.get("kc_mid")
    cyc = traits.get("indicative_cycle_duration")

    if et and et.get("low") is not None and et.get("high") is not None:
        et_mid = 0.5 * (float(et["low"]) + float(et["high"]))
        water_pct = int(round(max(22.0, min(95.0, (et_mid - 180.0) / 650.0 * 100.0))))
    elif kc and kc.get("high") is not None:
        water_pct = int(round(max(25.0, min(92.0, float(kc["high"]) * 62.0))))
    else:
        water_pct = 55

    cycle_min = int(cyc["low"]) if cyc and cyc.get("low") is not None else None
    cycle_max = int(cyc["high"]) if cyc and cyc.get("high") is not None else None

    out = dict(item)
    if item.get("family"):
        out["family"] = item["family"]
    else:
        out.pop("family", None)
    out["yield_tonnes_per_ha"] = _FAO_REFERENCE_YIELD_THA.get(cid, 4.2)
    out["water_percent"] = water_pct
    if cycle_min is not None and cycle_max is not None:
        out["cycle_days_min"] = cycle_min
        out["cycle_days_max"] = cycle_max
        out["growth_days"] = f"{cycle_min}-{cycle_max}d"
    if card is not None:
        out["suitability"] = card.get("status")
        out["reason"] = card.get("reason")
        out["summary"] = card.get("summary")
    return out


def _parse_regional_params(request: Request) -> dict | None:
    country = (request.query_params.get("country") or "").strip().upper() or None
    lat_raw = (request.query_params.get("latitude") or "").strip()
    lon_raw = (request.query_params.get("longitude") or "").strip()
    start_date = (request.query_params.get("start_date") or "").strip() or None
    ph_raw = (request.query_params.get("ph") or "").strip()
    drainage = (request.query_params.get("drainage") or "").strip() or None

    lat = float(lat_raw) if lat_raw else None
    lon = float(lon_raw) if lon_raw else None
    ph = float(ph_raw) if ph_raw else None

    if (lat is None or lon is None) and not country:
        return None
    return {
        "country": country,
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "ph": ph,
        "drainage": drainage,
    }


def _screen_region(params: dict | None) -> dict[str, dict] | None:
    if not params:
        return None
    country = params["country"]
    lat = params["latitude"]
    lon = params["longitude"]
    if lat is None or lon is None:
        regions = country_regions(country) if country else []
        if regions:
            lat = regions[0]["lat"]
            lon = regions[0]["lon"]
        else:
            default_farm = parse_farm({"country": country or "LK"})
            lat = default_farm.latitude
            lon = default_farm.longitude

    farm_payload: dict[str, object] = {
        "country": country or "LK",
        "latitude": lat,
        "longitude": lon,
    }
    if params["start_date"]:
        farm_payload["start_date"] = params["start_date"]
    if params["ph"] is not None:
        farm_payload["ph"] = params["ph"]
    if params["drainage"]:
        farm_payload["drainage"] = params["drainage"]

    farm = parse_farm(farm_payload)
    try:
        ds = get_dataset(lat, lon)
        cards = find_options(farm, ds)
        return {c["id"]: c for c in cards if c.get("id")}
    except (DataError, Exception):
        return None


async def crops_catalogue(request: Request) -> Response:
    """Search and paginate the reviewed knowledge catalogue (defaulting to supported rotation crops)."""
    q = (request.query_params.get("q") or "").strip()
    category = (request.query_params.get("category") or "").strip() or None
    include_catalogue = (request.query_params.get("include_catalogue") or "").lower() in {"1", "true", "yes"}
    try:
        limit = int(request.query_params.get("limit", "50"))
        offset = int(request.query_params.get("offset", "0"))
        regional_params = _parse_regional_params(request)

        def _run():
            supported_ids, by_crop = _build_crop_enrichment()
            card_by_id = _screen_region(regional_params)
            if include_catalogue:
                raw_items = search_crops(query=q, limit=limit, offset=offset, category=category)
                total = count_crops(query=q, category=category)
                items = [
                    _enrich_crop_item(
                        c,
                        by_crop.get(c["id"], {}),
                        card_by_id.get(c["id"]) if card_by_id else None,
                    )
                    for c in raw_items
                ]
            else:
                active_ids = supported_ids
                if card_by_id:
                    viable_ids = {
                        cid
                        for cid, card in card_by_id.items()
                        if card.get("status") in {"possible", "check"} and cid in supported_ids
                    }
                    if viable_ids:
                        active_ids = viable_ids
                all_matches = search_crops(query=q, limit=250, offset=0, category=category)
                filtered = [c for c in all_matches if c["id"] in active_ids]
                total = len(filtered)
                items = [
                    _enrich_crop_item(
                        c,
                        by_crop.get(c["id"], {}),
                        card_by_id.get(c["id"]) if card_by_id else None,
                    )
                    for c in filtered[offset : offset + limit]
                ]
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": items,
            }

        return json_response(await run_in_threadpool(_run))
    except ValueError as exc:
        return json_response({"error": str(exc)}, status_code=400)


async def knowledge_categories_endpoint(request: Request) -> Response:
    """Fetch reviewed crop categories from the active knowledge database."""
    include_catalogue = (request.query_params.get("include_catalogue") or "").lower() in {"1", "true", "yes"}
    try:
        regional_params = _parse_regional_params(request)

        def _run():
            if include_catalogue:
                return crop_categories()
            supported_ids, _ = _build_crop_enrichment()
            card_by_id = _screen_region(regional_params)
            active_ids = supported_ids
            if card_by_id:
                viable_ids = {
                    cid
                    for cid, card in card_by_id.items()
                    if card.get("status") in {"possible", "check"} and cid in supported_ids
                }
                if viable_ids:
                    active_ids = viable_ids
            all_crops = search_crops(limit=250, offset=0)
            return sorted({c["group_name"] for c in all_crops if c["id"] in active_ids and c.get("group_name")})

        cats = await run_in_threadpool(_run)
        return json_response({"categories": cats})
    except ValueError as exc:
        return json_response({"error": str(exc)}, status_code=400)
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
