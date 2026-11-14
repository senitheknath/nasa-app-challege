"""Adaptive WGS84 geometry normalization, zero-distortion polygon handling, and interior sampling."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from agroshift.config import get_precision_policy
from agroshift.identity.farm_records import polygon_area_hectares


def normalize_boundary(boundary: Any) -> dict | None:
    """Normalize GeoJSON Polygon, UI parcel {coordinates:[{lat,lng}]}, or [{lat,lng}] into GeoJSON Polygon."""
    if not boundary:
        return None
    if isinstance(boundary, dict):
        if boundary.get("type") == "Polygon" and isinstance(boundary.get("coordinates"), list):
            ring = boundary["coordinates"][0] if boundary["coordinates"] else []
            if len(ring) >= 3:
                closed = [[float(p[0]), float(p[1])] for p in ring if len(p) >= 2]
                if len(closed) >= 3:
                    if closed[0] != closed[-1]:
                        closed.append(closed[0])
                    return {"type": "Polygon", "coordinates": [closed]}
            return None
        raw_coords = boundary.get("coordinates")
        if isinstance(raw_coords, list):
            boundary = raw_coords
        else:
            return None
    if isinstance(boundary, list) and len(boundary) >= 3:
        ring: list[list[float]] = []
        for pt in boundary:
            if isinstance(pt, dict) and "lat" in pt and ("lng" in pt or "lon" in pt):
                lon = float(pt.get("lng", pt.get("lon")))
                lat = float(pt["lat"])
                ring.append([lon, lat])
            elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                ring.append([float(pt[1]), float(pt[0])])
        if len(ring) >= 3:
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            return {"type": "Polygon", "coordinates": [ring]}
    return None


def polygon_hash(poly: dict | None) -> str | None:
    if not poly:
        return None
    raw = json.dumps(poly, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def polygon_centroid(poly: dict | None) -> tuple[float, float] | None:
    """Compute (latitude, longitude) centroid from a normalized GeoJSON Polygon."""
    if not poly:
        return None
    ring = poly.get("coordinates", [[]])[0]
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    if not pts:
        return None
    mean_lon = sum(float(p[0]) for p in pts) / len(pts)
    mean_lat = sum(float(p[1]) for p in pts) / len(pts)
    return round(mean_lat, 5), round(mean_lon, 5)


def bbox_from_area_ha(lat: float, lon: float, area_ha: float) -> str:
    """Compute a square W,S,E,N bounding box centered at (lat, lon) covering area_ha hectares."""
    side_m = math.sqrt(max(float(area_ha), 0.01) * 10000.0)
    half_m = side_m / 2.0
    dlat = half_m / 111320.0
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    dlon = half_m / (111320.0 * cos_lat)
    return f"{lon - dlon:.5f},{lat - dlat:.5f},{lon + dlon:.5f},{lat + dlat:.5f}"


def parse_bbox_str(
    lat: float,
    lon: float,
    poly: dict | None = None,
    bbox: Any = None,
    area_ha: float | None = None,
    delta_deg: float = 0.1,
) -> str:
    """Derive bounding box string (W,S,E,N) from explicit bbox, polygon, area_ha, or point radius."""
    if bbox:
        if isinstance(bbox, str) and len(bbox.split(",")) == 4:
            return bbox.strip()
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            return f"{float(bbox[0]):.5f},{float(bbox[1]):.5f},{float(bbox[2]):.5f},{float(bbox[3]):.5f}"
        if isinstance(bbox, dict) and all(k in bbox for k in ("west", "south", "east", "north")):
            return f"{float(bbox['west']):.5f},{float(bbox['south']):.5f},{float(bbox['east']):.5f},{float(bbox['north']):.5f}"

    if poly:
        ring = poly["coordinates"][0]
        lons = [p[0] for p in ring if len(p) >= 2]
        lats = [p[1] for p in ring if len(p) >= 2]
        if lons and lats:
            return f"{min(lons):.5f},{min(lats):.5f},{max(lons):.5f},{max(lats):.5f}"

    if area_ha is not None and float(area_ha) > 0:
        return bbox_from_area_ha(lat, lon, float(area_ha))

    return f"{lon - delta_deg:.4f},{lat - delta_deg:.4f},{lon + delta_deg:.4f},{lat + delta_deg:.4f}"


def ensure_ccw_ring(ring: list[list[float]]) -> list[list[float]]:
    """Ensure polygon ring is counter-clockwise (required by NASA CMR polygon= parameter)."""
    pts = ring[:-1] if len(ring) > 1 and ring[0] == ring[-1] else list(ring)
    if len(pts) < 3:
        return ring
    signed_area = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i][0], pts[i][1]
        x2, y2 = pts[(i + 1) % len(pts)][0], pts[(i + 1) % len(pts)][1]
        signed_area += (x1 * y2) - (x2 * y1)
    ordered = list(pts) if signed_area >= 0 else list(reversed(pts))
    ordered.append(ordered[0])
    return ordered


def format_cmr_polygon(poly: dict, max_vertices: int = 250) -> str | None:
    """Format a GeoJSON Polygon into NASA CMR 'lon1,lat1,lon2,lat2,...' (CCW, closed)."""
    ring = poly.get("coordinates", [[]])[0]
    if len(ring) < 4:
        return None
    pts = ring[:-1] if ring[0] == ring[-1] else list(ring)
    if len(pts) > max_vertices:
        step = max(1, math.ceil(len(pts) / max_vertices))
        pts = pts[::step]
    ccw = ensure_ccw_ring(pts)
    return ",".join(f"{p[0]:.5f},{p[1]:.5f}" for p in ccw)


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test in WGS84 coordinates."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def sample_polygon_interior(
    poly: dict,
    center_lat: float,
    center_lon: float,
    max_points: int = 9,
) -> list[tuple[float, float]]:
    """Sample up to max_points strictly inside the polygon (with center fallback)."""
    ring = poly.get("coordinates", [[]])[0]
    if len(ring) < 4 or max_points <= 1:
        return [(center_lat, center_lon)]
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    grid_n = max(3, int(math.ceil(math.sqrt(max_points * 2))))
    candidates: list[tuple[float, float]] = []
    if _point_in_ring(center_lon, center_lat, ring):
        candidates.append((round(center_lat, 5), round(center_lon, 5)))

    for r in range(1, grid_n):
        lat = min_lat + (max_lat - min_lat) * (r / grid_n)
        for c in range(1, grid_n):
            lon = min_lon + (max_lon - min_lon) * (c / grid_n)
            if _point_in_ring(lon, lat, ring):
                pt = (round(lat, 5), round(lon, 5))
                if pt not in candidates:
                    candidates.append(pt)
                if len(candidates) >= max_points:
                    return candidates
    return candidates or [(center_lat, center_lon)]


def resolve_geometry(
    usage: str,
    latitude: float,
    longitude: float,
    *,
    boundary: Any = None,
    bbox: Any = None,
    area_ha: float | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve input shape into the configured spatial precision mode for a given usage."""
    policy = get_precision_policy(usage, config=config)
    configured_mode = str(policy.get("mode", "centroid"))
    poly = normalize_boundary(boundary)
    poly_area = polygon_area_hectares(poly) if poly else None
    effective_area = poly_area if poly_area is not None else area_ha
    delta_deg = float(policy.get("fallback_radius_deg", 0.1))

    active_mode = configured_mode
    points = [(float(latitude), float(longitude))]
    cmr_polygon: str | None = None
    bbox_str = parse_bbox_str(
        latitude, longitude, poly=poly, bbox=bbox, area_ha=effective_area, delta_deg=delta_deg
    )

    if configured_mode == "full_polygon":
        if poly:
            max_v = int(policy.get("max_vertices", 250))
            cmr_polygon = format_cmr_polygon(poly, max_vertices=max_v)
            points = sample_polygon_interior(poly, latitude, longitude, max_points=9)
        else:
            active_mode = str(policy.get("fallback_mode", "bbox"))
    elif configured_mode == "sampled_grid":
        min_area = float(policy.get("min_area_ha", 1.0))
        max_pts = int(policy.get("max_points", 9))
        if poly and (effective_area or 0.0) >= min_area:
            points = sample_polygon_interior(poly, latitude, longitude, max_points=max_pts)
        else:
            active_mode = "centroid"
    elif configured_mode == "bbox":
        active_mode = "bbox"
    else:
        active_mode = "centroid"

    p_hash = polygon_hash(poly) if (poly and active_mode in ("full_polygon", "sampled_grid")) else None
    cache_suffix = f"{active_mode}:{p_hash}" if p_hash else active_mode

    return {
        "usage": usage,
        "configured_mode": configured_mode,
        "active_mode": active_mode,
        "polygon": poly,
        "polygon_hash": p_hash,
        "cmr_polygon": cmr_polygon,
        "bbox": bbox_str,
        "points": points,
        "area_ha": effective_area,
        "cache_suffix": cache_suffix,
    }
