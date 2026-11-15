"""Validated, portable farm records. Measurements stay separate from map estimates."""

from dataclasses import asdict, fields
from datetime import datetime, timezone
import json
import math
import uuid

import pycountry
from agroshift.science.climate.climate import Window
from agroshift.science.decision.decision import Farm
from agroshift.science.climate.power import DataError


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def farm_from_dict(value):
    if not isinstance(value, dict) or set(value) != {f.name for f in fields(Farm)}:
        raise DataError("This farm file has an unsupported set of fields.")
    data = dict(value)
    try:
        if any(
            isinstance(data[k], bool) or not isinstance(data[k], (int, float))
            for k in ("latitude", "longitude")
        ):
            raise ValueError()
        for key in ("ph", "area_ha", "irrigation_mm", "rain_fraction"):
            if data[key] is not None and (
                type(data[key]) not in (float, int) or not math.isfinite(data[key])
            ):
                raise ValueError()
        if not isinstance(data["country"], str) or not pycountry.countries.get(
            alpha_2=data["country"]
        ):
            raise ValueError()
        if type(data["pilot_confirmed"]) is not bool:
            raise ValueError()
        for f in fields(Farm):
            if isinstance(f.default, str) and (
                not isinstance(data[f.name], str) or len(data[f.name]) > 200
            ):
                raise ValueError()
        for key in ("baseline", "allowed"):
            if (
                not isinstance(data[key], (list, tuple))
                or len(data[key]) > 20
                or not all(isinstance(x, str) for x in data[key])
            ):
                raise ValueError()
            data[key] = tuple(data[key])
        if not isinstance(data["windows"], (list, tuple)) or len(
            data["windows"]
        ) not in (1, 2):
            raise ValueError()
        windows = []
        for w in data["windows"]:
            if (
                not isinstance(w, dict)
                or set(w) != {f.name for f in fields(Window)}
                or not all(type(v) is int for v in w.values())
            ):
                raise ValueError()
            windows.append(Window(**w))
        data["windows"] = tuple(windows)
        farm = Farm(**data)
        farm.validate()
        return farm
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        raise DataError(
            "This farm file contains invalid measurements or dates."
        ) from exc


def boundary_polygon(value, farm):
    """One WGS84 ring, no holes, at most 250 vertices; must enclose the selected field point."""
    if value is None:
        return None
    try:
        if (
            not isinstance(value, dict)
            or value.get("type") != "Polygon"
            or set(value) != {"type", "coordinates"}
        ):
            raise ValueError()
        rings = value["coordinates"]
        if not isinstance(rings, list) or len(rings) != 1:
            raise ValueError()
        ring = rings[0]
        if (
            not isinstance(ring, list)
            or not 4 <= len(ring) <= 251
            or ring[0] != ring[-1]
        ):
            raise ValueError()
        for pair in ring:
            if (
                not isinstance(pair, (list, tuple))
                or len(pair) != 2
                or any(
                    type(n) not in (int, float) or not math.isfinite(n) for n in pair
                )
            ):
                raise ValueError()
            if not -180 <= pair[0] <= 180 or not -90 <= pair[1] <= 90:
                raise ValueError()
        # Reject repeated vertices, crossing edges, degenerate and antimeridian polygons.
        if (
            len(set(map(tuple, ring[:-1]))) != len(ring) - 1
            or max(p[0] for p in ring) - min(p[0] for p in ring) > 180
        ):
            raise ValueError()

        def orient(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        def on(a, b, c):
            return (
                abs(orient(a, b, c)) < 1e-12
                and min(a[0], b[0]) <= c[0] <= max(a[0], b[0])
                and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
            )

        def crosses(a, b, c, d):
            return (
                orient(a, b, c) * orient(a, b, d) < 0
                and orient(c, d, a) * orient(c, d, b) < 0
            ) or any((on(a, b, c), on(a, b, d), on(c, d, a), on(c, d, b)))

        edges = list(zip(ring, ring[1:]))
        for i, (a, b) in enumerate(edges):
            for j, (c, d) in enumerate(edges[i + 1 :], i + 1):
                if j == i + 1 or (i == 0 and j == len(edges) - 1):
                    continue
                if crosses(a, b, c, d):
                    raise ValueError()
        if abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in edges)) < 1e-12:
            raise ValueError()
        x, y = farm.longitude, farm.latitude
        inside = any(on(a, b, (x, y)) for a, b in edges)
        if not inside:
            count = sum(
                (a[1] > y) != (b[1] > y)
                and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]
                for a, b in edges
            )
            inside = bool(count % 2)
        if not inside:
            raise ValueError()
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        raise DataError(
            "Draw one non-crossing boundary around the selected field point (up to 250 corners)."
        ) from exc


def polygon_area_hectares(boundary: dict | None) -> float | None:
    """Compute geodetic area in hectares (ha) for a GeoJSON Polygon ring using WGS84 authalic spherical excess."""
    if not isinstance(boundary, dict) or boundary.get("type") != "Polygon":
        return None
    rings = boundary.get("coordinates")
    if not isinstance(rings, list) or not rings or not isinstance(rings[0], list) or len(rings[0]) < 4:
        return None
    ring = rings[0]
    r_earth = 6371008.8  # WGS84 authalic radius in meters
    total = 0.0
    try:
        for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:]):
            dlon = math.radians(float(lon2) - float(lon1))
            s_lat = math.sin(math.radians(float(lat1))) + math.sin(math.radians(float(lat2)))
            total += dlon * s_lat
        area_m2 = abs(total) * (r_earth ** 2) / 2.0
        area_ha = round(area_m2 / 10000.0, 2)
        return area_ha if area_ha >= 0.01 else 0.01
    except (TypeError, ValueError, OverflowError):
        return None


def profile(name, farm, label, boundary=None):
    if not isinstance(name, str) or not isinstance(label, str):
        raise DataError("Use text for the farm and location names.")
    name = name.strip()
    label = label.strip()
    if not 1 <= len(name) <= 80 or not 1 <= len(label) <= 120:
        raise DataError(
            "Use a farm name of 1–80 characters and a location name of 1–120 characters."
        )
    # Round-trip validation is shared by uploaded files and database writes.
    farm = farm_from_dict(asdict(farm))
    return dict(
        schema="agroshift.farm.v1",
        name=name,
        location_label=label,
        farm=asdict(farm),
        boundary=boundary_polygon(boundary, farm),
    )


def validate_profile(value):
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "name", "location_label", "farm", "boundary"}
        or value["schema"] != "agroshift.farm.v1"
    ):
        raise DataError("Choose an AgroShift farm profile export.")
    if len(json.dumps(value)) > 100_000:
        raise DataError("The farm file is too large.")
    return profile(
        value["name"],
        farm_from_dict(value["farm"]),
        value["location_label"],
        value["boundary"],
    )


def read_profile(body):
    try:
        if len(body) > 100_000:
            raise ValueError()
        return validate_profile(json.loads(body))
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise DataError("Choose a valid AgroShift farm profile under 100 KB.") from exc


def new_session_record(value, identifier=None, revision=0):
    return dict(
        id=identifier or str(uuid.uuid4()),
        revision=revision + 1,
        profile=validate_profile(value),
        updated_at=utc_now(),
    )
