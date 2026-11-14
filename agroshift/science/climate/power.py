"""NASA POWER access, validation, provenance and exact-request disk cache."""
from dataclasses import dataclass
from datetime import date, datetime, timezone
import csv
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import time

import pandas as pd
import requests

PARAMETERS = ("T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN")
EXTENDED_PARAMETERS = (
    "T2M",
    "T2M_MIN",
    "T2M_MAX",
    "PRECTOTCORR",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
    "WS2M",
    "WS10M",
    "PS",
    "T2MDEW",
    "GWETTOP",
    "GWETROOT",
)
ALLOWED_PARAMETERS = frozenset(EXTENDED_PARAMETERS)
ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"


class DataError(ValueError):
    """An actionable validation or provider failure."""


def coordinates(latitude: float, longitude: float) -> None:
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
               for v in (latitude, longitude)):
        raise DataError("Coordinates must be finite numbers.")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise DataError("Latitude must be −90…90 and longitude −180…180.")


def power_grid_cell(latitude: float, longitude: float) -> dict:
    """Return published NASA POWER MERRA-2 (0.5°×0.625°) and CERES (1°×1°) grid-cell metadata."""
    coordinates(latitude, longitude)
    met_lat = max(-90.0, min(90.0, round(round(float(latitude) / 0.5) * 0.5, 4)))
    met_lon = max(-180.0, min(180.0, round(round(float(longitude) / 0.625) * 0.625, 4)))
    sol_lat = max(-89.5, min(89.5, round(math.floor(float(latitude)) + 0.5, 4)))
    sol_lon = max(-179.5, min(179.5, round(math.floor(float(longitude)) + 0.5, 4)))
    return {
        "meteorology_grid": "0.5° latitude × 0.625° longitude",
        "meteorology_cell_center": [met_lat, met_lon],
        "meteorology_cell_bounds": [
            round(max(-90.0, met_lat - 0.25), 4),
            round(max(-180.0, met_lon - 0.3125), 4),
            round(min(90.0, met_lat + 0.25), 4),
            round(min(180.0, met_lon + 0.3125), 4),
        ],
        "solar_grid": "1.0° latitude × 1.0° longitude",
        "solar_cell_center": [sol_lat, sol_lon],
        "solar_cell_bounds": [
            round(max(-90.0, sol_lat - 0.5), 4),
            round(max(-180.0, sol_lon - 0.5), 4),
            round(min(90.0, sol_lat + 0.5), 4),
            round(min(180.0, sol_lon + 0.5), 4),
        ],
        "cell_id": f"met:{met_lat:+.3f},{met_lon:+.4f}|sol:{sol_lat:+.2f},{sol_lon:+.2f}",
    }


def grid_query_key(query: dict) -> str:
    """Normalized SHA-256 cache key for a NASA POWER grid cell + date range + parameters."""
    cell = power_grid_cell(query["latitude"], query["longitude"])
    normalized = {
        "cell_id": cell["cell_id"],
        "start": query["start"],
        "end": query["end"],
        "parameters": query["parameters"],
        "community": query.get("community", "AG"),
        "format": query.get("format", "JSON"),
        "time-standard": query.get("time-standard", "LST"),
    }
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()


def request_parameters(latitude, longitude, start, end, parameters=PARAMETERS):
    coordinates(latitude, longitude)
    if not isinstance(start, date) or not isinstance(end, date) or start > end:
        raise DataError("Provide a start date no later than the end date.")
    if start < date(1981, 1, 1) or end >= date.today() or (end-start).days > 31*366:
        raise DataError("Choose historical dates from 1981, up to 31 years per request.")
    if not parameters or not set(parameters) <= ALLOWED_PARAMETERS:
        raise DataError("Unsupported or empty NASA parameter selection.")
    return dict(latitude=latitude, longitude=longitude, start=start.strftime("%Y%m%d"),
                end=end.strftime("%Y%m%d"), parameters=",".join(parameters),
                community="AG", format="JSON", **{"time-standard": "LST"})


def parse_payload(payload, query):
    """Align dates, check units/ranges, and preserve missing observations as NaN."""
    try:
        series = payload["properties"]["parameter"]
        meta = payload["parameters"]
        fill = float(payload["header"]["fill_value"])
        if payload["header"].get("time_standard") != query["time-standard"]:
            raise DataError("NASA returned a different time standard.")
        index = pd.date_range(query["start"], query["end"], freq="D")
        frame = pd.DataFrame(index=index)
        issues = list(payload.get("messages", []))
        expected = set(index.strftime("%Y%m%d"))
        for name in query["parameters"].split(","):
            values = series[name]
            if not isinstance(values, dict) or set(values) - expected:
                raise DataError(f"Unexpected dates in {name}.")
            unit = meta[name]["units"]
            allowed = {
                "T2M": {"C"},
                "T2M_MIN": {"C"},
                "T2M_MAX": {"C"},
                "T2MDEW": {"C"},
                "PRECTOTCORR": {"mm/day"},
                "RH2M": {"%"},
                "ALLSKY_SFC_SW_DWN": {"MJ/m^2/day", "kW-hr/m^2/day", "kWh/m^2/day"},
                "WS2M": {"m/s"},
                "WS10M": {"m/s"},
                "PS": {"kPa"},
                "GWETTOP": {"1", "dimensionless", ""},
                "GWETROOT": {"1", "dimensionless", ""},
            }
            if unit not in allowed[name]:
                raise DataError(f"Unexpected unit for {name}: {unit}.")
            column = pd.Series(values, dtype="float64").replace(fill, float("nan"))
            column.index = pd.to_datetime(column.index, format="%Y%m%d")
            frame[name] = column.reindex(index)
            invalid = ~frame[name].map(lambda x: pd.isna(x) or math.isfinite(x))
            if name in ("PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "WS2M", "WS10M"):
                invalid |= frame[name] < 0
            if name == "PS":
                invalid |= frame[name] <= 0
            if name == "RH2M":
                invalid |= (frame[name] < 0) | (frame[name] > 100)
            if name in ("GWETTOP", "GWETROOT"):
                invalid |= (frame[name] < 0) | (frame[name] > 1)
            if invalid.any():
                issues.append(f"{name}: {int(invalid.sum())} invalid measurements set to missing.")
                frame.loc[invalid, name] = float("nan")
            if name == "ALLSKY_SFC_SW_DWN" and unit != "MJ/m^2/day":
                frame[name] *= 3.6
                issues.append("Solar energy converted from kWh/m²/day to MJ/m²/day (×3.6).")
        if not frame.notna().any().any():
            raise DataError("NASA returned no usable observations for this request.")
        if {"T2M_MIN", "T2M_MAX"} <= set(frame):
            inverted = frame.T2M_MIN > frame.T2M_MAX
            if inverted.any():
                frame.loc[inverted, ["T2M_MIN", "T2M_MAX"]] = float("nan")
                issues.append("Inverted minimum/maximum temperatures set to missing.")
        frame.index.name = "date"
        return frame, issues
    except DataError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise DataError(f"Unrecognized NASA response: {exc}") from exc


@dataclass
class Dataset:
    frame: pd.DataFrame
    provenance: dict
    issues: list


def unpack(envelope, mode, expected_query=None, allow_same_grid_cell=False):
    try:
        query = envelope["request"]
        if expected_query is not None:
            if not allow_same_grid_cell:
                if query != expected_query:
                    raise DataError("Cached request does not match the selected location and period.")
            else:
                if (any(query.get(k) != expected_query.get(k)
                        for k in ("start", "end", "parameters", "community", "format", "time-standard"))
                        or grid_query_key(query) != grid_query_key(expected_query)):
                    raise DataError("Cached request does not match the selected grid cell and period.")
        body = json.dumps(envelope["payload"], sort_keys=True).encode()
        if hashlib.sha256(body).hexdigest() != envelope["sha256"]:
            raise DataError("Cached data failed its integrity check.")
        payload = envelope["payload"]
        header = payload["header"]
        lon, lat = payload["geometry"]["coordinates"][:2]
        coordinates(query["latitude"], query["longitude"])
        coordinates(lat, lon)
        if (abs(lat-query["latitude"]) > 0.00051 or abs(lon-query["longitude"]) > 0.00051
                or any(header.get(k) != query[k] for k in ("start", "end"))
                or header.get("api", {}).get("name") != "POWER Daily API"
                or envelope["url"].split("?")[0] != ENDPOINT):
            raise DataError("NASA response metadata does not match the requested point, product or dates.")
        timestamp = datetime.fromisoformat(envelope["retrieved_at_utc"])
        if timestamp.utcoffset() is None:
            raise DataError("NASA retrieval timestamp must include its time zone.")
        frame, issues = parse_payload(payload, query)
        kind = "REAL" if mode == "live NASA request" else "VERIFIED_CACHE"
        target_lat = expected_query["latitude"] if expected_query is not None else query["latitude"]
        target_lon = expected_query["longitude"] if expected_query is not None else query["longitude"]
        frame.attrs.update(data_kind=kind, latitude=target_lat, longitude=target_lon)
        grid_meta = power_grid_cell(target_lat, target_lon)
        missing_days = frame.isna().sum().to_dict()
        provenance = {k: v for k, v in envelope.items() if k != "payload"}
        provenance.update(
            dataset_id="nasa_power_daily_ag",
            provider="NASA POWER",
            data_kind=kind,
            simulated=False,
            source="NASA POWER",
            product=header["title"],
            product_version=header.get("api", {}).get("version", "v2"),
            cache_status=mode,
            native_sources=header["sources"],
            requested_coordinates=[target_lon, target_lat],
            cached_request_coordinates=[query["longitude"], query["latitude"]],
            returned_coordinates=[lon, lat],
            grid_cell=grid_meta,
            grid_cell_reused=bool(
                expected_query is not None
                and (query["latitude"] != target_lat or query["longitude"] != target_lon)
            ),
            time_standard=query["time-standard"],
            date_range=[query["start"], query["end"]],
            parameters=query["parameters"].split(","),
            units={k: ("MJ/m^2/day" if k == "ALLSKY_SFC_SW_DWN" else payload["parameters"][k]["units"]) for k in frame},
            missing_days=missing_days,
            missing_data_indicators={
                "fill_value": header.get("fill_value"),
                "missing_days": missing_days,
                "has_missing_data": any(v > 0 for v in missing_days.values()),
            },
            processing="Daily LST alignment, fill and invalid values marked missing, solar converted to MJ/m²/day when needed.",
            mode=mode,
            header=envelope["payload"]["header"],
            parameter_metadata=envelope["payload"]["parameters"],
            meteorology_grid="0.5° latitude × 0.625° longitude",
            solar_grid="approximately 1° × 1°; source dependent",
        )
        return Dataset(frame, provenance, issues)
    except DataError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        raise DataError("Invalid cache envelope.") from exc


def load_snapshot(path):
    try:
        return unpack(json.loads(Path(path).read_text(encoding="utf-8")), "bundled NASA snapshot")
    except (OSError, ValueError) as exc:
        raise DataError(f"Could not load the recorded NASA snapshot: {exc}") from exc


def archived_history(query, mode="verified archive after NASA outage"):
    """Return an exact, hash-checked distributed snapshot or None."""
    _curr = Path(__file__).resolve()
    while _curr != _curr.parent:
        if (_curr / "data").is_dir() and (_curr / "agroshift").is_dir():
            ROOT = _curr
            break
        _curr = _curr.parent
    else:
        ROOT = Path(__file__).resolve().parents[3]
    root = ROOT / "data"
    manifest = root / "global_nasa_stations_summary.csv"
    if not manifest.exists():
        return None
    with manifest.open(encoding="utf-8") as rows:
        for row in csv.DictReader(rows):
            if (row.get("data_kind") != "VERIFIED_CACHE" or row["start"] != query["start"]
                    or row["end"] != query["end"] or float(row["latitude"]) != query["latitude"]
                    or float(row["longitude"]) != query["longitude"]):
                continue
            path = (root.parent / row["evidence"]).resolve()
            if not path.is_relative_to(root.resolve()):
                raise DataError("Invalid archive path in collection manifest.")
            try:
                raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
                envelope = json.loads(raw)
                if row["sha256"] != envelope["sha256"] or envelope["request"] != query:
                    continue
                return unpack(envelope, mode, query)
            except (OSError, ValueError, KeyError) as exc:
                raise DataError("The matching NASA archive could not be verified.") from exc
    return None


class PowerClient:
    def __init__(self, cache_dir=None, session=None, sleep=time.sleep):
        self.cache = Path(cache_dir or os.getenv("AGROSHIFT_CACHE_DIR", ".cache/power"))
        self.session = session or requests.Session()
        self.sleep = sleep

    def fetch(self, latitude, longitude, start, end, force=False, parameters=PARAMETERS, reuse_grid_cell=False):
        query = request_parameters(latitude, longitude, start, end, parameters)
        key = hashlib.sha256(json.dumps(query, sort_keys=True).encode()).hexdigest()
        path = self.cache / f"{key}.json"
        grid_path = (self.cache / "grid" / f"{grid_query_key(query)}.json") if reuse_grid_cell else None
        cached = None
        cached_allow_grid = False
        if path.exists():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                result = unpack(cached, "local cache", query)
                fetched = datetime.fromisoformat(cached["retrieved_at_utc"])
                age = (datetime.now(timezone.utc)-fetched).total_seconds()
                if not force and 0 <= age < 30*86400:
                    return result
            except (OSError, ValueError, TypeError, KeyError):
                cached = None
        if cached is None and grid_path is not None and grid_path.exists():
            try:
                cached = json.loads(grid_path.read_text(encoding="utf-8"))
                result = unpack(cached, "local grid-cell cache", query, allow_same_grid_cell=True)
                fetched = datetime.fromisoformat(cached["retrieved_at_utc"])
                age = (datetime.now(timezone.utc)-fetched).total_seconds()
                cached_allow_grid = True
                if not force and 0 <= age < 30*86400:
                    return result
            except (OSError, ValueError, TypeError, KeyError):
                cached = None
                cached_allow_grid = False
        error = "Unknown network error"
        for attempt in range(3):
            retry_delay = 2**attempt
            try:
                response = self.session.get(ENDPOINT, params=query, timeout=(10, 60))
                if response.status_code == 429 or response.status_code >= 500:
                    error = f"NASA is temporarily unavailable (HTTP {response.status_code})."
                    try:
                        retry_delay = min(10, max(retry_delay, float(response.headers.get("Retry-After", 0))))
                    except ValueError:
                        pass
                else:
                    if response.status_code != 200:
                        raise DataError(f"NASA rejected the request (HTTP {response.status_code}).")
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise DataError("NASA returned a non-JSON response.") from exc
                    parse_payload(payload, query)
                    envelope = dict(request=query, url=response.url,
                                    retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                                    schema_version=1, payload=payload,
                                    sha256=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest())
                    result = unpack(envelope, "live NASA request", query)
                    try:
                        self.cache.mkdir(parents=True, exist_ok=True)
                        with tempfile.NamedTemporaryFile(mode="w", dir=self.cache, delete=False, encoding="utf-8") as handle:
                            json.dump(envelope, handle)
                            tmp = handle.name
                        os.replace(tmp, path)
                        if grid_path is not None:
                            grid_path.parent.mkdir(parents=True, exist_ok=True)
                            with tempfile.NamedTemporaryFile(mode="w", dir=grid_path.parent, delete=False, encoding="utf-8") as ghandle:
                                json.dump(envelope, ghandle)
                                gtmp = ghandle.name
                            os.replace(gtmp, grid_path)
                    except OSError:
                        result.issues.append("Data loaded, but this host could not save a disk cache.")
                    return result
            except requests.RequestException as exc:
                error = f"NASA connection failed: {type(exc).__name__}."
            if attempt < 2:
                self.sleep(retry_delay)
        if cached:
            result = unpack(
                cached,
                "stale grid-cell cache after NASA outage" if cached_allow_grid else "stale cache after NASA outage",
                query,
                allow_same_grid_cell=cached_allow_grid,
            )
            result.issues.append(error + " Displaying the matching saved observations.")
            return result
        archived = archived_history(query)
        if archived is not None:
            archived.issues.append(error + " Using the matching archived observations.")
            return archived
        raise DataError(error + " Try again, shorten the period, or open the recorded demo.")
