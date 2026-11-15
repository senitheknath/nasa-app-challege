"""Tests for the Universal Spatial Cache, Satellite Active Monitoring, and Smart Field Auto-fill."""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from agroshift.earth_data import (
    cell_key,
    derive_field_autofill,
    fetch_satellite_overpasses,
    get_active_monitoring_layers,
    get_cached,
    get_connection,
    list_cached_types,
    set_cached,
)
from api.server import app


def test_geo_cache_crud_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test_geo.db"
    key = cell_key("soil_ph", 8.3114, 80.4037)
    assert key == "soil_ph:8.311:80.404"

    # Initially empty
    assert get_cached("soil_ph", 8.3114, 80.4037, db_path=db_file) is None

    # Write record
    payload = {"ph_h2o": 6.2, "depth_cm": [0, 5]}
    set_cached("soil_ph", 8.3114, 80.4037, payload, source="soilgrids_test", db_path=db_file)

    # Read back
    cached = get_cached("soil_ph", 8.3114, 80.4037, db_path=db_file)
    assert cached is not None
    assert cached["cached"] is True
    assert cached["source"] == "soilgrids_test"
    assert cached["data"]["ph_h2o"] == 6.2

    # Grouped stats
    stats = list_cached_types(db_path=db_file)
    assert stats.get("soil_ph") == 1


def test_satellite_active_monitoring_layers():
    layers = get_active_monitoring_layers(8.3114, 80.4037)
    assert len(layers) >= 3
    layer_ids = {l["id"] for l in layers}
    assert "smap_surface_soil_moisture" in layer_ids
    assert "modis_vegetation_vigor_ndvi" in layer_ids
    assert "gpm_imerg_precipitation_rate" in layer_ids

    for l in layers:
        if l["layer_type"] == "wmts":
            assert "{z}/{y}/{x}" in l["tile_url"]
        else:
            assert l["layer_type"] == "wms" and l["wms_url"]
        assert l["source"]


def test_satellite_overpasses_fetch_and_fallback():
    # Test offline reference fallback
    res = fetch_satellite_overpasses(8.3114, 80.4037, offline=True)
    assert res["acquisitions_count"] >= 2
    sensors = {a["sensor"] for a in res["acquisitions"]}
    assert "HLSL30" in sensors
    assert "SPL3SMP_E" in sensors
    for a in res["acquisitions"]:
        assert a["recurrence"]
        assert a["role"]


def test_field_autofill_derivation():
    poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [80.400, 8.310],
                [80.405, 8.310],
                [80.405, 8.315],
                [80.400, 8.315],
                [80.400, 8.310],
            ]
        ],
    }
    res = derive_field_autofill(8.3114, 80.4037, "LK", boundary=poly, offline=True)
    autofill = res["autofill"]
    assert "ph" in autofill
    assert "drainage" in autofill
    assert "area_ha" in autofill
    assert autofill["area_ha"]["value"] > 0
    assert autofill["area_ha"]["acres"] > 0
    assert autofill["ph"]["can_override"] is True
    assert autofill["drainage"]["can_override"] is True


def test_earth_data_api_endpoints_integration():
    client = TestClient(app)
    poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [80.400, 8.310],
                [80.405, 8.310],
                [80.405, 8.315],
                [80.400, 8.315],
                [80.400, 8.310],
            ]
        ],
    }
    auto_resp = client.post(
        "/api/earth-data/autofill",
        json={
            "country": "LK",
            "latitude": 8.3114,
            "longitude": 80.4037,
            "boundary": poly,
            "offline": True,
        },
    )
    assert auto_resp.status_code == 200
    auto_body = auto_resp.json()
    assert auto_body["autofill"]["area_ha"]["value"] == 30.59

    sat_resp = client.post(
        "/api/earth-data/satellite",
        json={
            "latitude": 8.3114,
            "longitude": 80.4037,
            "boundary": poly,
            "offline": True,
        },
    )
    assert sat_resp.status_code == 200
    sat_body = sat_resp.json()
    assert len(sat_body["layers"]) >= 3
    assert sat_body["overpass_schedule"]["acquisitions_count"] >= 2


def test_auth_and_farm_crud_integration(tmp_path: Path):
    import uuid
    client = TestClient(app)
    email = f"tester-{uuid.uuid4().hex[:8]}@agroshift.dev"

    # 1. Register
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "pass1234", "display_name": "Test Farmer"},
    )
    assert res.status_code == 200
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check /api/auth/me
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == email
    # 3. Save Farm
    save_res = client.post(
        "/api/farms",
        json={
            "name": "Anuradhapura Field A",
            "farm": {"country": "LK", "latitude": 8.3114, "longitude": 80.4037, "area_ha": 2.5},
            "boundary": None,
        },
        headers=headers,
    )
    assert save_res.status_code == 200
    farm_id = save_res.json()["farm"]["id"]

    # 4. List & Get Farm
    list_res = client.get("/api/farms", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["farms"]) == 1
    assert list_res.json()["farms"][0]["name"] == "Anuradhapura Field A"

    get_res = client.get(f"/api/farms/{farm_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["farm"]["id"] == farm_id

    # 5. Run rotations using saved farm_id
    rot_res = client.post(
        "/api/agronomy/rotations",
        json={
            "farm_id": farm_id,
            "windows": [
                {"start_month": 10, "start_day": 1, "end_month": 1, "end_day": 20},
                {"start_month": 3, "start_day": 1, "end_month": 6, "end_day": 30},
            ],
            "max_sequences": 3,
        },
        headers=headers,
    )
    assert rot_res.status_code == 200
    assert rot_res.json()["total"] == 3
    assert rot_res.json()["rotations"][0]["rank"] == 1

    # 6. Delete Farm
    del_res = client.delete(f"/api/farms/{farm_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # 7. Verify empty list
    list_res2 = client.get("/api/farms", headers=headers)
    assert len(list_res2.json()["farms"]) == 0
