"""Worldwide place names from GeoNames via Open-Meteo; manual coordinates also work."""
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
import os
import threading
import time
import requests

from agroshift.science.climate.power import DataError, coordinates
from agroshift.earth_data.provider_http import get

_places = OrderedDict()
_guard = threading.Lock()
_locks = [threading.Lock() for _ in range(17)]


def search_places(name, country_code=""):
    name = name.strip()
    if not 2 <= len(name) <= 150:
        raise DataError("Enter a place name between 2 and 150 characters.")
    code = str(country_code).strip().upper()
    if code and (not code.isascii() or not code.isalpha() or len(code) != 2):
        raise DataError("Choose a country from the list.")
    key = (name.casefold(), code)
    with _locks[hash(key) % len(_locks)]:
        with _guard:
            cached = _places.get(key)
        if cached and cached[0] >= time.monotonic():
            return [dict(p, access="cache") for p in deepcopy(cached[1])]
        params = dict(name=name, count=10, language="en", format="json")
        if code:
            params["countryCode"] = code
        api_key = os.getenv("OPEN_METEO_API_KEY")
        host = "customer-geocoding-api.open-meteo.com" if api_key else "geocoding-api.open-meteo.com"
        if api_key:
            params["apikey"] = api_key
        try:
            response = get(f"https://{host}/v1/search", params, stream=False)
            try:
                payload = response.json()
            finally:
                response.close()
            if not isinstance(payload, dict) or not isinstance(payload.get("results", []), list) or payload.get("error"):
                raise ValueError("Unexpected search response")
            results = []
            retrieved = datetime.now(timezone.utc).isoformat()
            for place in payload.get("results", [])[:10]:
                if not isinstance(place, dict) or not place.get("name"):
                    raise ValueError("Malformed place")
                coordinates(place.get("latitude"), place.get("longitude"))
                if code and place.get("country_code") and place["country_code"] != code:
                    continue
                results.append(dict(place, access="live", retrieved_at=retrieved, source="GeoNames via Open-Meteo"))
            with _guard:
                _places[key] = (time.monotonic() + 86400, deepcopy(results))
                _places.move_to_end(key)
                while len(_places) > 128:
                    _places.popitem(last=False)
            return results
        except (requests.RequestException, ValueError) as exc:
            if cached:
                return [dict(p, access="cache") for p in deepcopy(cached[1])]
            raise DataError("Place search is unavailable. Enter coordinates or use the map.") from exc


def pilot_scope(latitude, longitude, country, confirmed):
    # A region-specific comparison also needs grower confirmation.
    return country == "LK" and 5.8 <= latitude <= 9.9 and 79.5 <= longitude <= 82.0 and confirmed
