"""Offline land check and exact historical weather for the location chosen by a farmer."""

from datetime import date
from functools import lru_cache
import csv
import gzip
import json
from pathlib import Path

from agroshift.science.climate.power import (
    DataError,
    PowerClient,
    PARAMETERS,
    archived_history,
    coordinates,
    request_parameters,
)

_curr = Path(__file__).resolve()
while _curr != _curr.parent:
    if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
        ROOT = _curr
        break
    _curr = _curr.parent
else:
    ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


@lru_cache(maxsize=1)
def geometry():
    with gzip.open(DATA / "boundaries.json.gz", "rt", encoding="utf8") as f:
        return json.load(f)["polygons"]


def inside(x, y, ring):
    hit = False
    a, b = ring[-1]
    for c, d in ring:
        if (b > y) != (d > y) and x < (c - a) * (y - b) / (d - b) + a:
            hit = not hit
        a, b = c, d
    return hit


def countries_at(lat, lon):
    coordinates(lat, lon)
    return {
        cc
        for cc, (west, south, east, north), rings in geometry()
        if west <= lon <= east
        and south <= lat <= north
        and inside(lon, lat, rings[0])
        and not any(inside(lon, lat, r) for r in rings[1:])
    }


@lru_cache(maxsize=1)
def stations():
    with (DATA / "global_nasa_stations_summary.csv").open(encoding="utf8") as f:
        rows = [r for r in csv.DictReader(f) if r["data_kind"] == "VERIFIED_CACHE"]
    return {
        r["hub_key"]: (r["country"], float(r["latitude"]), float(r["longitude"]))
        for r in rows
    }


@lru_cache(maxsize=1)
def country_atlas():
    path = DATA / "global_countries_agro_atlas.csv"
    if not path.exists():
        return {}
    out = {}
    with path.open(encoding="utf8") as f:
        for r in csv.DictReader(f):
            cc = (r.get("country_code") or "").strip()
            if not cc:
                continue
            try:
                lat = float(r["latitude"]) if r.get("latitude") else None
                lon = float(r["longitude"]) if r.get("longitude") else None
            except ValueError:
                lat, lon = None, None
            out[cc] = {
                "country_code": cc,
                "country_name": r.get("country_name", cc),
                "continent": r.get("continent", ""),
                "latitude": lat,
                "longitude": lon,
                "hemisphere": r.get("hemisphere", ""),
                "default_season": r.get("default_season", ""),
            }
    return out


@lru_cache(maxsize=1)
def _largest_country_polygons():
    by_cc = {}
    for cc, bbox, rings in geometry():
        w, s, e, n = bbox
        area = (e - w) * (n - s)
        if cc not in by_cc or area > by_cc[cc][0]:
            by_cc[cc] = (area, bbox, rings)
    return by_cc


@lru_cache(maxsize=512)
def country_map_view(cc: str) -> dict:
    """Return an accurate interior land center and zoom level for any ISO-2 country code."""
    atlas = country_atlas().get(cc, {})
    by_cc = _largest_country_polygons()
    if cc in by_cc:
        _, (w, s, e, n), rings = by_cc[cc]
        lat = (s + n) / 2.0
        lon = (w + e) / 2.0
        span = max(e - w, n - s)
        zoom = (
            8
            if span < 2
            else (7 if span < 5 else (6 if span < 12 else (5 if span < 25 else 4)))
        )
        ring = rings[0]
        if not (inside(lon, lat, ring) and not any(inside(lon, lat, r) for r in rings[1:])):
            best = None
            best_dist = 1e9
            for fy in (0.5, 0.45, 0.55, 0.4, 0.6, 0.35, 0.65, 0.3, 0.7, 0.25, 0.75):
                cy = s + fy * (n - s)
                for fx in (
                    0.5,
                    0.45,
                    0.55,
                    0.4,
                    0.6,
                    0.35,
                    0.65,
                    0.3,
                    0.7,
                    0.25,
                    0.75,
                    0.2,
                    0.8,
                ):
                    cx = w + fx * (e - w)
                    if inside(cx, cy, ring) and not any(inside(cx, cy, r) for r in rings[1:]):
                        d = (cx - lon) ** 2 + (cy - lat) ** 2
                        if d < best_dist:
                            best_dist = d
                            best = (cy, cx)
            if best is not None:
                lat, lon = best
            else:
                xs = [p[0] for p in ring]
                ys = [p[1] for p in ring]
                lat, lon = sum(ys) / len(ys), sum(xs) / len(xs)
        return {
            "lat": round(float(lat), 4),
            "lon": round(float(lon), 4),
            "zoom": int(zoom),
            "continent": atlas.get("continent", ""),
            "hemisphere": atlas.get("hemisphere", ""),
            "default_season": atlas.get("default_season", ""),
            "country_name": atlas.get("country_name", cc),
        }
    if atlas and atlas.get("latitude") is not None and atlas.get("longitude") is not None:
        return {
            "lat": round(float(atlas["latitude"]), 4),
            "lon": round(float(atlas["longitude"]), 4),
            "zoom": 6,
            "continent": atlas.get("continent", ""),
            "hemisphere": atlas.get("hemisphere", ""),
            "default_season": atlas.get("default_season", ""),
            "country_name": atlas.get("country_name", cc),
        }
    return {
        "lat": 7.8731,
        "lon": 80.7718,
        "zoom": 6,
        "continent": "",
        "hemisphere": "",
        "default_season": "",
        "country_name": cc,
    }


SUBNATIONAL_AGRO_REGIONS = {
    "LK": [
        ("Anuradhapura · North Central Dry Zone (DL1b)", 8.3114, 80.4037),
        ("Polonnaruwa · Mahaweli System (DL1c)", 7.9403, 81.0188),
        ("Kurunegala · North Western Intermediate Zone (IL1a)", 7.4863, 80.3623),
        ("Hambantota · Southern Dry Zone (DL5)", 6.1246, 81.1185),
        ("Ampara · Eastern Gal Oya Basin (DL2b)", 7.2975, 81.6820),
        ("Jaffna · Northern Dry Zone (DL3)", 9.6615, 80.0255),
        ("Vavuniya · Northern Dry Zone (DL1b)", 8.7542, 80.4982),
        ("Monaragala · Uva Wellassa Dry/Intermediate (DL1a/IL1c)", 6.8728, 81.3507),
        ("Badulla · Uva Up-Country Intermediate (IU3)", 6.9934, 81.0550),
        ("Kandy · Mid-Country Wet Zone (WM2b)", 7.2906, 80.6337),
        ("Matale · Mid-Country Intermediate (IM3)", 7.4675, 80.6234),
        ("Puttalam · North Western Dry Zone (DL1f)", 8.0362, 79.8283),
    ],
    "IN": [
        ("Ludhiana · Punjab Indo-Gangetic Plains", 30.9010, 75.8573),
        ("Nagpur · Vidarbha Central Deccan Cotton/Pulse Belt", 21.1458, 79.0882),
        ("Coimbatore · Tamil Nadu Southern Plateau", 11.0168, 76.9558),
        ("Karnal · Haryana Rice-Wheat Corridor", 29.6857, 76.9905),
        ("Varanasi · Eastern Gangetic Plain", 25.3176, 82.9739),
    ],
    "KE": [
        ("Nairobi / Central Highlands", -1.2921, 36.8219),
        ("Eldoret · Rift Valley Maize Breadbasket", 0.5143, 35.2698),
        ("Kisumu · Lake Victoria Basin", -0.0917, 34.7680),
        ("Machakos · Eastern Semi-Arid Mixed Farming", -1.5177, 37.2634),
    ],
    "US": [
        ("Ames · Iowa Corn/Soybean Belt", 42.0308, -93.6319),
        ("Fresno · California Central Valley Irrigated Hub", 36.7378, -119.7871),
        ("Lubbock · Texas High Plains", 33.5779, -101.8552),
        ("Stoneville · Mississippi Delta", 33.4240, -90.9151),
    ],
    "BR": [
        ("Sinop · Mato Grosso Cerrado Grain Belt", -11.8608, -55.5095),
        ("Londrina · Paraná Subtropical Farming Zone", -23.3045, -51.1696),
        ("Petrolina · São Francisco Irrigated Fruit/Crop Valley", -9.3891, -40.5030),
    ],
    "AU": [
        ("Wagga Wagga · NSW Riverina Mixed Farming", -35.1082, 147.3598),
        ("Toowoomba · Queensland Darling Downs", -27.5598, 151.9507),
        ("Merredin · Western Australia Wheatbelt", -31.4827, 118.2789),
    ],
    "NG": [
        ("Kano · Northern Sudan Savanna Grain Belt", 12.0022, 8.5920),
        ("Ibadan · South-West Derived Savanna", 7.3775, 3.9470),
    ],
    "ET": [
        ("Addis Ababa / Shewa Central Highlands", 8.9806, 38.7578),
        ("Bahir Dar · Amhara Lake Tana Basin", 11.5742, 37.3614),
    ],
}


def country_regions(cc: str) -> list[dict]:
    """Return agro-climatic hubs and regional presets for quick map/location selection."""
    view = country_map_view(cc)
    out = []
    seen = set()
    for label, lat, lon in SUBNATIONAL_AGRO_REGIONS.get(cc, []):
        key = (round(lat, 2), round(lon, 2))
        seen.add(key)
        out.append({"label": label, "lat": lat, "lon": lon, "zoom": 9})
    for k, (st_cc, lat, lon) in stations().items():
        if st_cc == cc:
            key = (round(lat, 2), round(lon, 2))
            if key not in seen:
                seen.add(key)
                out.append(
                    {
                        "label": f"{k.replace('_', ' ').title()} (Verified Weather Hub)",
                        "lat": lat,
                        "lon": lon,
                        "zoom": 9,
                    }
                )
    out.append(
        {
            "label": f"{view['country_name']} · National Center ({view['lat']:.2f}, {view['lon']:.2f})",
            "lat": view["lat"],
            "lon": view["lon"],
            "zoom": view["zoom"],
        }
    )
    return out


def load_history(lat, lon, first=2001, last=2025, refresh=False):
    start, end = date(first, 1, 1), date(last, 12, 31)
    if not refresh:
        archive = archived_history(
            request_parameters(lat, lon, start, end, PARAMETERS),
            "verified bundled NASA archive",
        )
        if archive is not None:
            return archive
    return PowerClient().fetch(lat, lon, start, end, force=refresh)
