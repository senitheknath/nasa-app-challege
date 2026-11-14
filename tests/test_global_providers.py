"""Recorded-source contract and deterministic outages. These tests perform no network I/O."""
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
import requests

from agroshift import provider_http as http
from agroshift import providers as p
from agroshift.geography import search_places
from agroshift.power import DataError


@pytest.fixture(autouse=True)
def cold_cache():
    http._cache.clear()
    http._cooldown.clear()
    yield
    http._cache.clear()
    http._cooldown.clear()


def test_gaez_observed_layers_water_scenario_and_ocean():
    a = p.gaez_point(-1.28333, 36.81667, "Maize", "rainfed")
    b = p.gaez_point(-1.28333, 36.81667, "Maize", "irrigated")
    assert a["value"] == "Very marginal" and b["value"] == "Marginal"
    assert a["source"] != b["source"] and a["kind"] == "modelled" and a["access"] == "archive"
    assert p.gaez_point(0, -140, "Maize", "rainfed")["value"] is None
    assert p.gaez_point(8.3, 80.4, "Maize", "unknown")["status"] == "unavailable"
    assert p.gaez_point(8.3, 80.4, "Rye")["value"] is None
    for crop in p.GAEZ_CROPS:
        for water in p.WATER:
            r = p.gaez_point(8.3114, 80.4037, crop, water)
            assert r["status"] == "verified" and 1 <= r["class_code"] <= 8


def test_soil_unavailable_and_exact_archived_point(monkeypatch):
    monkeypatch.setattr(http, "_load_remote", Mock(side_effect=requests.Timeout))
    recorded = p.soil_context(8.3114, 80.4037)
    assert (recorded["value"], recorded["access"], recorded["kind"]) == (5.8, "archive", "modelled")
    assert p.soil_context(8.314, 80.4037)["value"] is None
    assert p.soil_context(-1.28333, 36.81667, offline=True)["value"] == 6.1


def test_archive_integrity_failure_is_unavailable(tmp_path, monkeypatch):
    original = http.ARCHIVES
    monkeypatch.setattr(http, "ARCHIVES", tmp_path)
    for source in original.glob("*.json"):
        doc = json.loads(source.read_bytes())
        doc["sha256"] = "0" * 64
        (tmp_path/source.name).write_text(json.dumps(doc))
    assert p.soil_context(8.3114, 80.4037, offline=True)["value"] is None


def test_reference_deduplicates_and_does_not_cross_language(monkeypatch):
    ref = p.terminology("maize", offline=True)
    assert ref["value"][0]["uri"].endswith("c_12332")
    assert p.terminology("maíz", "es", offline=True)["value"][0]["language"] == "es"
    assert p.terminology("maíz", "fr", offline=True)["value"] is None
    url = "https://example.invalid/test"
    read = Mock(return_value=(b'["grain"]', "2026-11-08T00:00:00+00:00"))
    monkeypatch.setattr(http, "_load_remote", read)
    def call(_):
        return http.reference(url, {}, json.loads, kind="test", detail="fixture")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(call, range(4)))
    assert read.call_count == 1
    assert all(x["value"] == ["grain"] for x in results)


def test_429_respects_retry_after(monkeypatch):
    response = Mock(status_code=429, headers={"Retry-After": "120"})
    request = Mock(return_value=response)
    monkeypatch.setattr(http.requests, "get", request)
    for _ in range(2):
        with pytest.raises(DataError, match="rate limit"):
            http.get("https://limit.test/path", {})
    request.assert_called_once()


def test_calendar_keeps_zones_and_ignores_unavailable_dates(monkeypatch):
    # Minimal synthetic API shape to exercise missing/corrupt dates without redistributing the API.
    row = {"crop": {"id":"0002", "name":"Fixture crop"}, "aez":{"name":"Fixture zone"}, "sessions":[
        {"early_sowing":{"month":"11","day":"2"}, "later_sowing":{}, "additional_information":"Main"}]}
    def fetch(*_):
        return json.dumps([row]).encode(), "2026-11-08T00:00:00+00:00"
    monkeypatch.setattr(http, "_load_remote", fetch)
    result = p.crop_calendars("KE", "0002")
    assert result["value"][0]["sow_to"] is None
    assert result["value"][0]["sow_from"] == "2 Nov"
    assert result["value"][0]["zone"] == "Fixture zone"
    assert p.crop_calendars("KE", "0003")["value"] is None
    http._cache.clear()
    row["id_country"] = "LK"
    assert p.crop_calendars("KE", "0002")["value"] is None


def test_country_stats_and_modelled_country_sample_keep_dimensions():
    stat = p.national_production("KE", year=2023)
    assert stat["value"]["tonnes"] == 4285206 and stat["value"]["flag_meaning"] == "Official figure"
    assert stat["kind"] == "national statistic"
    assert p.national_production("KE", year=1800)["value"] is None
    au = p.gaez_context("AU", offline=True)
    assert au["value"] and au["value"][0]["period"] == "1981-2000"
    assert au["value"][0]["system"] == "Irrigation and high input level of management"
    assert p.gaez_context("KE", crop="Rye", offline=True)["value"] == []


def test_geocoding_retries_transient_failure_and_excludes_wrong_country(monkeypatch):
    good = Mock(status_code=200)
    good.json.return_value = {"results":[{"name":"Demo","latitude":0,"longitude":1,"country_code":"US"}]}
    request = Mock(side_effect=[requests.Timeout(), good])
    monkeypatch.setattr(http.requests,"get",request)
    assert search_places("Fixture village", "KE") == []
    assert request.call_count == 2
    assert search_places("Fixture village", "KE") == [] and request.call_count == 2
