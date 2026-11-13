"""Public evidence for Research. No connector writes into farm measurements or scores."""
import calendar
import csv
from datetime import date
from functools import lru_cache
import hashlib
from io import BytesIO, StringIO
import json
import math
from pathlib import Path
import re

from PIL import Image
import pycountry

from .power import DataError, coordinates
from .provider_http import reference

DATA = Path(__file__).resolve().parent.parent / "data"
AGROVOC = "https://agrovoc.fao.org/browse/rest/v1/search/"
CALENDAR = "https://api-cropcalendar.apps.fao.org/api/v1/countries"
SOIL = "https://maps.isric.org/mapserv"
GAEZ = "https://data.apps.fao.org/catalog/dataset/514c92d5-9e01-4c70-814a-80ea1ca9fe6a"
GAEZ_SUMMARY = "https://data.apps.fao.org/catalog/dataset/a55c337e-f7e6-4d2f-aa8e-6d2199171c37/resource/30c09503-8f35-447c-a1c6-d6c53d601335/download/gaez-sample.csv"
FAOSTAT = "https://www.fao.org/faostat/en/#data/QCL"
GAEZ_CROPS = {
    "Maize": "MZE",
    "Wheat": "WHE",
    "Groundnut": "GRD",
    "Soybean": "SOY",
    "Sorghum": "SRG",
    "White potato": "WPO",
    "Wetland rice": "RCW",
    "Dryland rice": "RCD",
    "Gram": "GRM",
    "Cowpea": "COW",
    "Chickpea": "CHK",
    "Pigeonpea": "PIG",
    "Phaseolus bean": "PHB",
    "Cassava": "CSV",
    "Sweet potato": "SPO",
    "Pearl millet": "PML",
    "Sunflower": "SFL",
    "Sesame": "SES",
    "Cotton": "COT",
    "Sugarcane": "SUC",
    "Banana": "BAN",
    "Tomato": "TOM",
    "Onion": "ONI",
    "Cabbage": "CAB",
}
GAEZ_CROP_ID_MAP = {
    "maize": "Maize",
    "wheat": "Wheat",
    "groundnut": "Groundnut",
    "soybean": "Soybean",
    "sorghum": "Sorghum",
    "potato": "White potato",
    "rice": "Wetland rice",
    "mung_bean": "Gram",
    "cowpea": "Cowpea",
    "chickpea": "Chickpea",
    "pigeon_pea": "Pigeonpea",
    "common_bean": "Phaseolus bean",
    "cassava": "Cassava",
    "sweet_potato": "Sweet potato",
    "pearl_millet": "Pearl millet",
    "sunflower": "Sunflower",
    "sesame": "Sesame",
    "cotton": "Cotton",
    "sugarcane": "Sugarcane",
    "banana": "Banana",
    "tomato": "Tomato",
    "onion": "Onion",
    "cabbage": "Cabbage",
}
GAEZ_CLASSES = ("No data", "Very high", "High", "Good", "Medium", "Moderate", "Marginal", "Very marginal", "Not suitable", "Water")
GAEZ_SCALE = [
    ("Very high", "#007000", "#FFFFFF"),
    ("High", "#15AE11", "#FFFFFF"),
    ("Good", "#ACE15E", "#1B2A21"),
    ("Medium", "#FFE853", "#1B2A21"),
    ("Moderate", "#FFAE34", "#1B2A21"),
    ("Marginal", "#FF6B35", "#FFFFFF"),
    ("Very marginal", "#D72638", "#FFFFFF"),
    ("Not suitable", "#7A7A7A", "#FFFFFF"),
]
WATER = {"rainfed": "LRLM", "irrigated": "LILM"}


def provider_registry():
    """Dated checks rather than a current uptime promise."""
    return json.loads((DATA / "provider_registry.json").read_text(encoding="utf-8"))


def _country(code):
    item = pycountry.countries.get(alpha_2=str(code).upper())
    if item is None:
        raise DataError("Choose a country from the list.")
    return item


def _missing(source, kind, detail):
    return dict(status="unavailable", source=source, kind=kind, detail=detail, value=None, access=None, retrieved_at=None)


def terminology(query, language="en", *, offline=False, record=False):
    query = str(query).strip()
    if not 2 <= len(query) <= 80 or any(c in query for c in "*?"):
        raise DataError("Enter 2–80 letters or words without a wildcard.")
    if language not in {"en", "fr", "es", "ar", "zh", "ru"}:
        raise DataError("Choose one of the six FAO languages.")
    def parse(body):
        rows = json.loads(body)["results"]
        if not isinstance(rows, list):
            raise ValueError("Missing AGROVOC results")
        out = []
        for row in rows:
            uri = row["uri"]
            if (row.get("vocab") != "agrovoc" or row.get("lang") != language
                    or not re.fullmatch(r"https?://aims\.fao\.org/aos/agrovoc/[A-Za-z0-9_-]+", uri)):
                continue
            if isinstance(row.get("prefLabel"), str) and row["prefLabel"].strip():
                out.append({"name": row["prefLabel"], "language": language, "uri": uri,
                            "matched_name": row.get("altLabel") or row["prefLabel"]})
        return out
    return reference(AGROVOC, {"query": query, "lang": language, "maxhits": 10}, parse,
                     kind="terminology", detail="FAO AGROVOC concept names and identifiers.",
                     offline=offline, record=record)


def _valid_list(body):
    rows = json.loads(body)
    if not isinstance(rows, list):
        raise ValueError("Malformed calendar response")
    return rows


def calendar_crops(country_code, *, offline=False, record=False):
    code = _country(country_code).alpha_2
    def parse(body):
        out = {}
        for row in _valid_list(body):
            if row["id_country"] != code:
                raise ValueError("Calendar country differs")
            crop_id = str(row["crop_id"])
            if not re.fullmatch(r"[0-9]{1,8}", crop_id) or not row.get("crop_name"):
                raise ValueError("Calendar crop has no identity")
            out[crop_id] = {"id": crop_id, "name": row["crop_name"]}
        return sorted(out.values(), key=lambda item: item["name"])
    return reference(f"{CALENDAR}/{code}/crops", {"language": "en"}, parse,
                     kind="zone reference", detail="FAO Crop Calendar crop names for the selected country.",
                     offline=offline, record=record)


def _month_day(record):
    if not isinstance(record, dict) or not record.get("month") or not record.get("day"):
        return None
    month, day = int(record["month"]), int(record["day"])
    date(2000, month, day)
    return f"{day} {calendar.month_abbr[month]}"


def crop_calendars(country_code, crop_id, *, offline=False, record=False):
    code = _country(country_code).alpha_2
    crop_id = str(crop_id)
    if not re.fullmatch(r"[0-9]{1,8}", crop_id):
        raise DataError("Choose a crop from the calendar list.")
    def parse(body):
        out = []
        for row in _valid_list(body):
            # Filtered responses may omit id_country. The request URL binds the country.
            if row.get("id_country", code) != code or str(row["crop"]["id"]) != crop_id:
                raise ValueError("Calendar does not match the selected country and crop")
            for session in row["sessions"]:
                out.append({"crop": row["crop"]["name"], "zone": row["aez"]["name"],
                            "season": session.get("additional_information"), "updated": row.get("lastUpdated"),
                            "sow_from": _month_day(session.get("early_sowing")), "sow_to": _month_day(session.get("later_sowing")),
                            "harvest_from": _month_day(session.get("early_harvest")), "harvest_to": _month_day(session.get("late_harvest"))})
        return out
    return reference(f"{CALENDAR}/{code}/cropCalendar", {"crop": crop_id, "language": "en"}, parse,
                     kind="zone reference", detail="Published dates for named zones. Confirm the zone of your field.",
                     offline=offline, record=record)


def _pixel_at(image, lat, lon):
    tags = image.tag_v2
    keys = tags.get(34735, ())
    if (2048, 0, 1, 4326) not in [tuple(keys[i:i+4]) for i in range(4, len(keys), 4)]:
        raise ValueError("Raster does not identify WGS84")
    scale_x, scale_y, _ = tags[33550]
    i, j, _, x, y, _ = tags[33922]
    if not (scale_x > 0 and scale_y > 0):
        raise ValueError("Unknown raster transform")
    col = math.floor(i + (lon - x) / scale_x)
    row = math.floor(j + (y - lat) / scale_y)
    if not (0 <= col < image.width and 0 <= row < image.height):
        raise ValueError("Point outside returned raster")
    return image.getpixel((col, row))


def soil_context(latitude, longitude, *, offline=False, record=False):
    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    detail = "ISRIC SoilGrids 2.0 modelled mean pH in water, 0–5 cm depth, 250 m source grid."
    kind = "modelled"
    if abs(lat) > 89.995 or abs(lon) > 179.995:
        return _missing(SOIL, kind, "No soil sample at this map edge.")
    crs = "http://www.opengis.net/def/crs/EPSG/0/4326"
    params = {"map": "/map/phh2o.map", "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCoverage",
              "COVERAGEID": "phh2o_0-5cm_mean", "FORMAT": "GEOTIFF_INT16", "SCALESIZE": "x(5),y(5)",
              "SUBSETTINGCRS": crs, "OUTPUTCRS": crs,
              "SUBSET": [f"X({lon-.005:.7f},{lon+.005:.7f})", f"Y({lat-.005:.7f},{lat+.005:.7f})"]}
    def parse(body):
        with Image.open(BytesIO(body)) as grid:
            if grid.format != "TIFF" or grid.size != (5, 5):
                raise ValueError("Unexpected SoilGrids raster size")
            raw = _pixel_at(grid, lat, lon)
            if not isinstance(raw, int) or not 0 < raw <= 140 or str(raw) == str(grid.tag_v2.get(42113)):
                raise DataError("No usable SoilGrids pH estimate at this location.")
            return raw / 10
    return reference(SOIL, params, parse, kind=kind, detail=detail, offline=offline, record=record,
                     source="https://docs.isric.org/globaldata/soilgrids/WCS_from_Python.html")


def gaez_context(country_code, crop="Wheat", *, offline=False, record=False):
    country = _country(country_code)
    def parse(body):
        rows = csv.DictReader(StringIO(body.decode("utf-8-sig")))
        if not {"iso3","Crop","SUIT_S","time_period","water_input","geographic_level","LC","EXC","AEZ","climate_data_source","ssp"} <= set(rows.fieldnames or []):
            raise ValueError("Missing GAEZ dimensions")
        out = []
        for row in rows:
            if row["iso3"] == country.alpha_3 and row["Crop"].casefold() == crop.casefold() and row["geographic_level"] == "Country":
                km2 = float(row["SUIT_S"])
                if not math.isfinite(km2) or km2 < 0:
                    raise ValueError("Invalid class area")
                out.append({"crop": row["Crop"], "country": row["country"], "suitable_class_km2": km2,
                            "period": row["time_period"], "system": row["water_input"], "climate": row["climate_data_source"],
                            "scenario": row["ssp"], "land_cover": row["LC"], "exclusion": row["EXC"], "zone": row["AEZ"]})
        return out
    return reference(GAEZ_SUMMARY, {}, parse, kind="modelled", detail="Area in the 'Suitable' class in FAO's country sample (km²).",
                     offline=offline, record=record)


@lru_cache(maxsize=1)
def _gaez_manifest():
    return json.loads((DATA / "gaez" / "manifest.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def _gaez_image(filename, digest):
    body = (DATA / "gaez" / filename).read_bytes()
    if hashlib.sha256(body).hexdigest() != digest:
        raise ValueError("Raster integrity failure")
    img = Image.open(BytesIO(body))
    if img.size != (4320, 2160) or img.mode != "P":
        raise ValueError("Unexpected GAEZ layer geometry")
    img.load()
    return img


def gaez_point(latitude, longitude, crop, water=None):
    coordinates(latitude, longitude)
    crop_code = GAEZ_CROPS.get(crop)
    system_code = WATER.get(water)
    if not crop_code or not system_code:
        return _missing(GAEZ, "modelled", "No matching GAEZ layer in this release.")
    name = f"GAEZ-V5.RES05-SIX.HP0120.AGERA5.HIST.{crop_code}.{system_code}.tif"
    try:
        record = _gaez_manifest()[name]
        image = _gaez_image(name, record["sha256"])
        # The eastern edge and south pole lie on the open boundary of the last cell.
        lon = -180.0 if longitude == 180 else float(longitude)
        lat = max(float(latitude), -90 + 1e-8)
        category = _pixel_at(image, lat, lon)
        if category not in range(1, 9):
            return _missing(record["url"], "modelled", "This GAEZ cell is water or has no land classification.")
        return {"value": GAEZ_CLASSES[category], "kind": "modelled", "status": "verified", "source": record["url"],
                "retrieved_at": record["retrieved_at"], "access": "archive", "class_code": category,
                "detail": f"FAO/IIASA GAEZ v5, {crop}, {water}, low inputs, 2001–2020 historical climate. About 10 km."}
    except (OSError, KeyError, ValueError, TypeError):
        return _missing(GAEZ, "modelled", "The GAEZ raster could not be verified.")


def national_production(country_code, crop="Maize (corn)", year=2023):
    country = _country(country_code)
    try:
        doc = json.loads((DATA / "faostat_qcl_sample.json").read_text(encoding="utf-8"))
        content = json.dumps(doc["rows"], sort_keys=True, ensure_ascii=False).encode()
        if hashlib.sha256(content).hexdigest() != doc["rows_sha256"]:
            raise ValueError("FAOSTAT extract integrity failure")
        match = next((r for r in doc["rows"] if r["country_code"] == country.alpha_2
                      and r["crop"].casefold() == crop.casefold() and r["year"] == int(year)), None)
        if match:
            return dict(status="verified", kind="national statistic", value=match, access="archive",
                        source=doc["source"], retrieved_at=doc["retrieved_at"],
                        detail=f"FAOSTAT QCL, {country.name} total production in {year}.")
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return _missing(FAOSTAT, "national statistic", "No verified national production record for this selection.")


def gaez_polygon(boundary: dict, crop: str, water: str = "rainfed") -> dict:
    """Sample all 5-arc-minute GAEZ v5 cells intersected by a validated farm polygon."""
    if not isinstance(boundary, dict):
        raise DataError("Field boundary must be a valid GeoJSON Polygon or Feature.")
    geom = boundary.get("geometry") if boundary.get("type") == "Feature" else boundary
    if not isinstance(geom, dict) or geom.get("type") != "Polygon":
        raise DataError("Field boundary must have a Polygon geometry.")
    rings = geom.get("coordinates")
    if not isinstance(rings, list) or not rings or not isinstance(rings[0], list) or len(rings[0]) < 4:
        raise DataError("Polygon requires an exterior coordinate ring with at least 4 positions.")
    ring = rings[0]
    lons = [float(pt[0]) for pt in ring]
    lats = [float(pt[1]) for pt in ring]
    for lat_v, lon_v in zip(lats, lons):
        coordinates(lat_v, lon_v)
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    c_lat = sum(lats[:-1]) / max(len(lats) - 1, 1)
    c_lon = sum(lons[:-1]) / max(len(lons) - 1, 1)

    center_res = gaez_point(c_lat, c_lon, crop, water)
    if center_res.get("status") != "verified":
        return center_res

    step = 1.0 / 12.0  # 5 arc-minutes
    sample_points = {(round(c_lat, 5), round(c_lon, 5))}
    for lon_v, lat_v in ring[:-1]:
        sample_points.add((round(lat_v, 5), round(lon_v, 5)))
    lat_cur = min_lat
    while lat_cur <= max_lat + 1e-9:
        lon_cur = min_lon
        while lon_cur <= max_lon + 1e-9:
            sample_points.add((round(lat_cur, 5), round(lon_cur, 5)))
            lon_cur += step
        lat_cur += step

    classes_found = {}
    for s_lat, s_lon in sorted(sample_points):
        pt_res = gaez_point(s_lat, s_lon, crop, water)
        if pt_res.get("status") == "verified":
            code = pt_res["class_code"]
            classes_found[code] = classes_found.get(code, 0) + 1

    distinct = [GAEZ_CLASSES[k] for k in sorted(classes_found)]
    return {
        "value": center_res["value"],
        "class_code": center_res["class_code"],
        "polygon_classes": distinct,
        "sampled_points": len(sample_points),
        "spans_multiple_cells": len(classes_found) > 1,
        "kind": "modelled",
        "status": "verified",
        "source": center_res["source"],
        "retrieved_at": center_res["retrieved_at"],
        "access": "archive",
        "resolution_note": (
            "FAO/IIASA GAEZ v5 has a 5-arc-minute (~10 km) grid resolution; "
            "a farm polygon reflects regional agro-ecological zone suitability rather than sub-field variation."
        ),
        "detail": center_res["detail"],
    }


def soil_profile_wcs(
    latitude: float,
    longitude: float,
    *,
    properties: tuple[str, ...] = ("phh2o", "clay", "sand", "silt", "soc", "bdod", "cec", "cfvo", "wv0033", "wv1500"),
    depths: tuple[str, ...] = ("0-5cm", "5-15cm", "15-30cm"),
    quantiles: tuple[str, ...] = ("mean", "Q0.05", "Q0.95"),
    offline: bool = False,
    record: bool = False,
) -> dict:
    """Retrieve multi-property, multi-depth ISRIC SoilGrids 2.0 WCS layers with uncertainty and pedological interpretation."""
    from .soil import SOILGRIDS_DEPTHS, SOILGRIDS_PROPERTIES, interpret_soil_profile, normalize_soilgrids_value

    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    if abs(lat) > 89.995 or abs(lon) > 179.995:
        return _missing(SOIL, "modelled", "No soil sample at this map edge.")

    crs = "http://www.opengis.net/def/crs/EPSG/0/4326"
    layers_by_depth: dict[str, dict] = {d: {} for d in depths if d in SOILGRIDS_DEPTHS}
    provenance_cells = []
    any_verified = False
    retrieved_at = None

    for prop in properties:
        if prop not in SOILGRIDS_PROPERTIES:
            continue
        for depth in depths:
            if depth not in SOILGRIDS_DEPTHS:
                continue
            q_entry = {}
            for q in quantiles:
                cov_id = f"{prop}_{depth}_{q}"
                params = {
                    "map": f"/map/{prop}.map",
                    "SERVICE": "WCS",
                    "VERSION": "2.0.1",
                    "REQUEST": "GetCoverage",
                    "COVERAGEID": cov_id,
                    "FORMAT": "GEOTIFF_INT16",
                    "SCALESIZE": "x(5),y(5)",
                    "SUBSETTINGCRS": crs,
                    "OUTPUTCRS": crs,
                    "SUBSET": [f"X({lon-.005:.7f},{lon+.005:.7f})", f"Y({lat-.005:.7f},{lat+.005:.7f})"],
                }

                def _parse_cell(body, p_name=prop):
                    with Image.open(BytesIO(body)) as grid:
                        if grid.format != "TIFF" or grid.size != (5, 5):
                            raise ValueError("Unexpected SoilGrids raster size")
                        raw = _pixel_at(grid, lat, lon)
                        if not isinstance(raw, int) or str(raw) == str(grid.tag_v2.get(42113)):
                            raise DataError(f"No usable SoilGrids {p_name} estimate at this location.")
                        norm = normalize_soilgrids_value(p_name, raw)
                        if not norm["valid"]:
                            raise DataError(f"Out-of-range SoilGrids {p_name} estimate.")
                        return norm

                res = reference(
                    SOIL,
                    params,
                    _parse_cell,
                    kind="modelled",
                    detail=f"ISRIC SoilGrids 2.0 {cov_id} (250 m source grid).",
                    offline=offline,
                    record=record,
                    source="https://docs.isric.org/globaldata/soilgrids/WCS_from_Python.html",
                )
                if res["status"] == "verified" and isinstance(res["value"], dict):
                    any_verified = True
                    retrieved_at = retrieved_at or res["retrieved_at"]
                    q_entry[q] = res["value"]["normalized_value"]
                    if q == "mean":
                        q_entry["raw_mean"] = res["value"]["raw_value"]
                        q_entry["original_unit"] = res["value"]["original_unit"]
                        q_entry["normalized_unit"] = res["value"]["normalized_unit"]
                        q_entry["conversion_method"] = res["value"]["conversion_method"]
                    provenance_cells.append(
                        {
                            "coverage_id": cov_id,
                            "access": res["access"],
                            "retrieved_at": res["retrieved_at"],
                            **res["value"],
                        }
                    )
            if q_entry:
                layers_by_depth[depth][prop] = q_entry

    # Fallback to top-5cm pH archive if only phh2o_0-5cm_mean is archived offline
    if not any_verified:
        top_ph = soil_context(lat, lon, offline=offline, record=False)
        if top_ph["status"] == "verified" and top_ph["value"] is not None:
            any_verified = True
            retrieved_at = top_ph["retrieved_at"]
            raw_equiv = int(round(float(top_ph["value"]) * 10))
            norm = normalize_soilgrids_value("phh2o", raw_equiv)
            layers_by_depth.setdefault("0-5cm", {})["phh2o"] = {
                "mean": norm["normalized_value"],
                "raw_mean": norm["raw_value"],
                "original_unit": norm["original_unit"],
                "normalized_unit": norm["normalized_unit"],
                "conversion_method": norm["conversion_method"],
            }

    if not any_verified:
        return _missing(SOIL, "modelled", "No verified SoilGrids profile layers available for this request.")

    interpretation = interpret_soil_profile(layers_by_depth)
    ph_top = layers_by_depth.get("0-5cm", {}).get("phh2o", {})
    return {
        "status": "verified",
        "kind": "modelled",
        "data_category": "modelled_estimate",
        "source": "https://docs.isric.org/globaldata/soilgrids/WCS_from_Python.html",
        "retrieved_at": retrieved_at,
        "access": provenance_cells[0]["access"] if provenance_cells else "archive",
        "value": interpretation["topsoil_0_30cm"].get("ph_h2o") or ph_top.get("mean"),
        "q05": ph_top.get("Q0.05"),
        "q95": ph_top.get("Q0.95"),
        "layers_by_depth": layers_by_depth,
        "topsoil_0_30cm": interpretation["topsoil_0_30cm"],
        "provenance_cells": provenance_cells,
        "scientific_safeguards": interpretation["scientific_safeguards"],
        "detail": "ISRIC SoilGrids 2.0 multi-depth WCS profile (~250 m grid). Modelled estimate, not a field soil test.",
    }


def usda_sda_soil(latitude: float, longitude: float, country_code: str = "US", *, offline: bool = False, record: bool = False) -> dict:
    """Query USDA NRCS Soil Data Access (SSURGO) for United States coordinates only."""
    coordinates(latitude, longitude)
    if str(country_code).upper() != "US":
        return _missing(
            "https://sdmdataaccess.sc.egov.usda.gov/",
            "regional_survey",
            "USDA NRCS Soil Data Access (SSURGO) covers United States territories only.",
        )
    lat, lon = float(latitude), float(longitude)
    # Check bundled/archived benchmark observations first when offline
    if offline:
        from .knowledge import soil_observations

        obs = [
            o
            for o in soil_observations("US")
            if abs(o["latitude"] - lat) < 0.05 and abs(o["longitude"] - lon) < 0.05
        ]
        if obs:
            top = obs[0]
            return {
                "status": "verified",
                "kind": "regional_survey",
                "data_category": "modelled_estimate",
                "source": "https://sdmdataaccess.sc.egov.usda.gov/",
                "access": "archive",
                "retrieved_at": top["retrieved_on"],
                "ph_h2o": top["normalized_value"],
                "value": top,
                "detail": "USDA NRCS SSURGO soil survey map-unit estimate (archived US benchmark).",
            }
        return _missing(
            "https://sdmdataaccess.sc.egov.usda.gov/",
            "regional_survey",
            "No offline USDA SDA archive for this coordinate.",
        )

    import requests

    sql = (
        "SELECT TOP 1 m.mukey, m.muname, c.compname, c.comppct_r, c.drainagecl, c.taxclname, "
        "ch.hzdept_r, ch.hzdepb_r, ch.ph1to1h2o_r, ch.claytotal_r, ch.sandtotal_r, ch.silttotal_r, "
        "ch.om_r, ch.dbthirdbar_r, ch.cec7_r "
        f"FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({lon:.5f} {lat:.5f})') i "
        "JOIN mapunit m ON i.mukey = m.mukey "
        "JOIN component c ON m.mukey = c.mukey AND c.majcompflag = 'Yes' "
        "LEFT JOIN chorizon ch ON c.cokey = ch.cokey AND ch.hzdept_r = 0 "
        "ORDER BY c.comppct_r DESC"
    )
    try:
        resp = requests.post(
            "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest",
            json={"query": sql, "format": "JSON+COLUMNNAME"},
            timeout=(5, 12),
        )
        resp.raise_for_status()
        table = resp.json().get("Table", [])
        if len(table) < 2:
            return _missing("https://sdmdataaccess.sc.egov.usda.gov/", "regional_survey", "No SSURGO map unit returned.")
        headers, vals = table[0], table[1]
        row = dict(zip(headers, vals))
        ph_val = float(row["ph1to1h2o_r"]) if row.get("ph1to1h2o_r") not in (None, "") else None
        return {
            "status": "verified",
            "kind": "regional_survey",
            "data_category": "modelled_estimate",
            "source": "https://sdmdataaccess.sc.egov.usda.gov/",
            "access": "live",
            "retrieved_at": date.today().isoformat(),
            "ph_h2o": ph_val,
            "value": {
                "mukey": row.get("mukey"),
                "muname": row.get("muname"),
                "component": row.get("compname"),
                "component_pct": float(row["comppct_r"]) if row.get("comppct_r") else None,
                "drainage_class": row.get("drainagecl"),
                "taxonomy": row.get("taxclname"),
                "ph_h2o": ph_val,
                "clay_pct": float(row["claytotal_r"]) if row.get("claytotal_r") else None,
                "sand_pct": float(row["sandtotal_r"]) if row.get("sandtotal_r") else None,
                "silt_pct": float(row["silttotal_r"]) if row.get("silttotal_r") else None,
                "organic_matter_pct": float(row["om_r"]) if row.get("om_r") else None,
                "bulk_density_g_cm3": float(row["dbthirdbar_r"]) if row.get("dbthirdbar_r") else None,
                "cec_cmol_kg": float(row["cec7_r"]) if row.get("cec7_r") else None,
            },
            "detail": f"USDA NRCS SSURGO map unit '{row.get('muname')}' ({row.get('compname')}, {row.get('drainagecl')}).",
        }
    except Exception:
        return _missing("https://sdmdataaccess.sc.egov.usda.gov/", "regional_survey", "USDA SDA service unreachable.")


def wosis_profiles(latitude: float, longitude: float, radius_deg: float = 0.5, *, offline: bool = False, record: bool = False) -> dict:
    """Retrieve standardized reference soil profile observations from ISRIC WoSIS WFS 2.0."""
    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    r = max(0.05, min(float(radius_deg), 2.0))
    params = {
        "map": "/map/wosis_latest.map",
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": "ms:wosis_latest_phaq",
        "OUTPUTFORMAT": "geojson",
        "COUNT": "10",
        "BBOX": f"{lat-r:.4f},{lon-r:.4f},{lat+r:.4f},{lon+r:.4f},EPSG:4326",
    }

    def _parse(body):
        data = json.loads(body.decode("utf-8"))
        features = data.get("features", [])
        rows = []
        for f in features:
            props = f.get("properties", {})
            if props.get("value_avg") is None:
                continue
            rows.append(
                {
                    "profile_code": props.get("profile_code"),
                    "country_name": props.get("country_name"),
                    "upper_depth_cm": float(props.get("upper_depth", 0)),
                    "lower_depth_cm": float(props.get("lower_depth", 0)),
                    "ph_h2o": float(props["value_avg"]),
                    "observation_date": props.get("date"),
                    "dataset_code": props.get("dataset_code"),
                }
            )
        return rows

    res = reference(
        SOIL,
        params,
        _parse,
        kind="reference_profile_observation",
        detail="ISRIC WoSIS standardized reference soil profiles within search radius (not the farmer's own field test).",
        offline=offline,
        record=record,
        source="https://www.isric.org/explore/wosis",
    )
    if res["status"] != "verified" and offline:
        from .knowledge import soil_observations

        nearby = [
            o
            for o in soil_observations()
            if o["observation_kind"] == "measured_profile"
            and abs(o["latitude"] - lat) <= r
            and abs(o["longitude"] - lon) <= r
        ]
        if nearby:
            return {
                "status": "verified",
                "kind": "reference_profile_observation",
                "source": "https://www.isric.org/explore/wosis",
                "access": "archive",
                "retrieved_at": nearby[0]["retrieved_on"],
                "value": nearby,
                "detail": "ISRIC WoSIS standardized reference soil profiles (offline benchmark archive).",
            }
    return res


def chirps_context(latitude: float, longitude: float, *, nasa_seasonal_rain_mm: float | None = None) -> dict:
    """Evaluate CHIRPS v3.0 quasi-global (60°S–60°N) rainfall coverage and non-averaging safeguard."""
    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    url = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/"
    if not (-60.0 <= lat <= 60.0):
        return _missing(
            url,
            "satellite_gauge_precip",
            f"Latitude {lat:.2f}° is outside CHIRPS v3.0 quasi-global land coverage (60°S–60°N).",
        )
    return {
        "status": "verified",
        "kind": "satellite_gauge_precip",
        "source": url,
        "access": "metadata",
        "retrieved_at": "2026-11-09",
        "coverage_bounds": {"latitude": [-60.0, 60.0], "longitude": [-180.0, 180.0]},
        "spatial_resolution": "0.05° × 0.05° (~5.5 km)",
        "temporal_coverage": "1981–present",
        "averaged_with_nasa_power": False,
        "nasa_seasonal_rain_mm": nasa_seasonal_rain_mm,
        "detail": (
            "CHIRPS v3.0 (UCSB CHC, 0.05° quasi-global 60°S–60°N infrared + gauge precipitation). "
            "Preserved with source-specific uncertainty and never automatically averaged with NASA POWER MERRA-2."
        ),
    }


def era5_land_context(
    latitude: float,
    longitude: float,
    start_date: str = "2023-01-01",
    end_date: str = "2023-01-10",
    *,
    offline: bool = False,
    record: bool = False,
) -> dict:
    """Retrieve complementary ECMWF ERA5-Land (~9 km) reanalysis context without treating soil moisture as field measurements."""
    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean,precipitation_sum,shortwave_radiation_sum,wind_speed_10m_max,soil_moisture_0_to_7cm_mean",
        "models": "era5_land",
        "timezone": "UTC",
    }

    def _parse(body):
        payload = json.loads(body.decode("utf-8"))
        daily = payload.get("daily", {})
        if not daily or "time" not in daily:
            raise ValueError("Missing ERA5-Land daily series")
        sm = [v for v in daily.get("soil_moisture_0_to_7cm_mean", []) if v is not None]
        t2m = [v for v in daily.get("temperature_2m_mean", []) if v is not None]
        rain = [v for v in daily.get("precipitation_sum", []) if v is not None]
        return {
            "days": len(daily["time"]),
            "temperature_mean_c": round(sum(t2m) / len(t2m), 2) if t2m else None,
            "precipitation_total_mm": round(sum(rain), 2) if rain else None,
            "surface_soil_moisture_m3_m3": round(sum(sm) / len(sm), 3) if sm else None,
            "soil_moisture_classification": "reanalysis_model_estimate",
            "resolution": "0.1° × 0.1° (~9 km)",
        }

    return reference(
        url,
        params,
        _parse,
        kind="reanalysis_model_estimate",
        detail="ECMWF ERA5-Land (0.1° ~9 km reanalysis). Soil moisture is a land-surface model estimate, not a field measurement.",
        offline=offline,
        record=record,
        source="https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land",
    )


def terrain_context(latitude: float, longitude: float, *, offline: bool = False, record: bool = False) -> dict:
    """Retrieve Copernicus DEM GLO-90 (90 m) elevation and local terrain slope context."""
    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    url = "https://api.open-meteo.com/v1/elevation"
    d = 0.00081  # ~90 m spacing
    params = {
        "latitude": f"{lat:.5f},{lat+d:.5f},{lat-d:.5f},{lat:.5f},{lat:.5f}",
        "longitude": f"{lon:.5f},{lon:.5f},{lon:.5f},{lon+d:.5f},{lon-d:.5f}",
    }

    def _parse(body):
        elevs = json.loads(body.decode("utf-8")).get("elevation", [])
        if not isinstance(elevs, list) or len(elevs) < 5:
            raise ValueError("Incomplete DEM response")
        c, n, s, e, w = [float(x) for x in elevs[:5]]
        dy_m = 2.0 * d * 111320.0
        dx_m = max(10.0, 2.0 * d * 111320.0 * math.cos(math.radians(lat)))
        dz_dy = (n - s) / dy_m
        dz_dx = (e - w) / dx_m
        slope_pct = round(math.hypot(dz_dx, dz_dy) * 100.0, 2)
        min_nbr = min(n, s, e, w)
        mean_nbr = (n + s + e + w) / 4.0
        local_relief_m = round(max(0.0, c - min_nbr), 2)
        concavity_m = round(c - mean_nbr, 2)
        low_lying = local_relief_m <= 1.2 and slope_pct < 1.5 and concavity_m <= 0.3
        drain_prior = "waterlogged" if low_lying else "well_drained"
        return {
            "elevation_m": round(c, 1),
            "regional_slope_pct": slope_pct,
            "local_relief_m": local_relief_m,
            "concavity_m": concavity_m,
            "suggested_drainage_prior": drain_prior,
            "why_we_think_this": (
                f"Copernicus DEM shows {c:.0f} m elevation with {slope_pct:.1f}% slope and "
                f"{local_relief_m:.1f} m height above nearest local drainage ("
                + ("low-lying basin — check for waterlogging" if low_lying else "sheds surface water — likely well-drained")
                + ")."
            ),
            "dem_resolution_m": 90,
            "slope_class": (
                "flat_to_gentle (<2%)"
                if slope_pct < 2.0
                else ("moderate (2-8%)" if slope_pct < 8.0 else "steep (>=8%)")
            ),
            "scale_disclaimer": "Derived from 90 m Copernicus DEM; does not capture field-level terracing, bunds, or micro-topography.",
        }

    return reference(
        url,
        params,
        _parse,
        kind="digital_elevation_model",
        detail="Copernicus DEM GLO-90 (~90 m) elevation, slope, and local drainage relief estimate.",
        offline=offline,
        record=record,
    )


def seasonal_outlook_context(
    latitude: float, longitude: float, *, offline: bool = False, record: bool = False
) -> dict:
    """Retrieve Open-Meteo Seasonal Forecast (ECMWF SEAS5 / sub-seasonal) 90-day outlook for rain, temperature, and root-zone soil moisture."""
    coordinates(latitude, longitude)
    lat, lon = float(latitude), float(longitude)
    url = "https://seasonal-api.open-meteo.com/v1/seasonal"
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "daily": "temperature_2m_mean,precipitation_sum,soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean",
        "forecast_days": "92",
        "timezone": "UTC",
    }

    def _parse(body):
        payload = json.loads(body.decode("utf-8"))
        daily = payload.get("daily", {})

        def _series(prefix: str) -> list[float]:
            for k, v in daily.items():
                if k == prefix or k.startswith(prefix + "_member"):
                    vals = [float(x) for x in (v or []) if isinstance(x, (int, float))]
                    if vals:
                        return vals
            return []

        temps = _series("temperature_2m_mean")
        rains = _series("precipitation_sum")
        sm_top = _series("soil_moisture_0_to_7cm_mean")
        sm_root = _series("soil_moisture_7_to_28cm_mean")
        if not temps and not rains:
            raise ValueError("Empty seasonal forecast response")
        return {
            "horizon_days": max(len(temps), len(rains)),
            "outlook_rain_total_mm": round(sum(rains[:90]), 1) if rains else None,
            "outlook_temp_mean_c": round(sum(temps[:90]) / len(temps[:90]), 2) if temps else None,
            "soil_moisture_0_7cm_m3m3": round(sum(sm_top[:90]) / len(sm_top[:90]), 3) if sm_top else None,
            "soil_moisture_7_28cm_m3m3": round(sum(sm_root[:90]) / len(sm_root[:90]), 3) if sm_root else None,
            "spatial_resolution": "~36 km (ECMWF SEAS5 ensemble)",
            "forecast_disclaimer": (
                "Forward-looking ~36 km ensemble seasonal outlook (Open-Meteo / ECMWF SEAS5). "
                "Strictly isolated from historical NASA POWER crop screening."
            ),
        }

    return reference(
        url,
        params,
        _parse,
        kind="seasonal_forecast_outlook",
        detail="Open-Meteo / ECMWF SEAS5 90-day seasonal precipitation, temperature, and root-zone soil moisture outlook.",
        source="https://open-meteo.com/en/docs/seasonal-forecast-api",
        offline=offline,
        record=record,
    )


def _parse_calendar_day(label: str | None) -> tuple[int, int] | None:
    if not label or not isinstance(label, str):
        return None
    parts = label.strip().split()
    if len(parts) != 2:
        return None
    try:
        day = int(parts[0])
        month = list(calendar.month_abbr).index(parts[1][:3].title())
        return (month, day)
    except (ValueError, IndexError):
        return None


def _month_in_span(month: int, start_m: int, end_m: int) -> bool:
    if start_m <= end_m:
        return start_m <= month <= end_m
    return month >= start_m or month <= end_m


def match_crop_calendar(window, calendar_rows: list[dict] | None, crop_name: str | None = None) -> dict:
    """Compare farmer-selected growing window against published FAO Crop Calendar zone windows without overwriting farmer dates."""
    if not calendar_rows:
        return {
            "status": "unavailable",
            "matched_zones": [],
            "conflicting_zones": [],
            "sowing_date_confirmed": False,
            "summary": "No published FAO Crop Calendar zone dates loaded for this country and crop.",
        }
    matched = []
    conflicts = []
    for row in calendar_rows:
        if crop_name and row.get("crop") and crop_name.casefold() not in row["crop"].casefold():
            continue
        sow_start = _parse_calendar_day(row.get("sow_from"))
        sow_end = _parse_calendar_day(row.get("sow_to"))
        harv_start = _parse_calendar_day(row.get("harvest_from"))
        harv_end = _parse_calendar_day(row.get("harvest_to"))
        if not (sow_start and sow_end and harv_start and harv_end):
            continue
        sow_ok = _month_in_span(window.start_month, sow_start[0], sow_end[0])
        harv_ok = _month_in_span(window.end_month, harv_start[0], harv_end[0])
        entry = {
            "zone": row.get("zone"),
            "season": row.get("season"),
            "sow_window": f"{row.get('sow_from')} – {row.get('sow_to')}",
            "harvest_window": f"{row.get('harvest_from')} – {row.get('harvest_to')}",
            "sowing_matches": sow_ok,
            "harvest_matches": harv_ok,
        }
        if sow_ok and harv_ok:
            matched.append(entry)
        else:
            conflicts.append(entry)

    if matched:
        zones_str = ", ".join(m["zone"] for m in matched[:3] if m.get("zone"))
        summary = f"Selected window ({window.label}) aligns with FAO Crop Calendar sowing and harvest windows in: {zones_str}."
    elif conflicts:
        c0 = conflicts[0]
        summary = (
            f"Selected window ({window.label}) differs from published FAO Crop Calendar dates "
            f"(e.g., {c0['zone']}: sow {c0['sow_window']}, harvest {c0['harvest_window']}). "
            "Farmer-selected dates are preserved."
        )
    else:
        summary = "No matching crop sessions found in the FAO Crop Calendar payload."

    return {
        "status": "matched" if matched else ("conflict" if conflicts else "no_sessions"),
        "matched_zones": matched,
        "conflicting_zones": conflicts,
        "sowing_date_confirmed": bool(matched),
        "farmer_window_preserved": True,
        "summary": summary,
    }
