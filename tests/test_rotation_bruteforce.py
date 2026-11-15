"""Verification tests for brute-force rotation planning and season-free API payloads."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from agroshift.climate import Window
from agroshift.decision import Farm
from agroshift.power import load_snapshot
from agroshift.rotation import engine as rotation_engine
from agroshift.rotation import plan_global_rotations
from agroshift.rotation import timeline_adapter
from api.server import app

ROOT = Path(__file__).resolve().parent.parent
DEMO_SNAPSHOT = ROOT / "data" / "demo_power.json"


def _assert_valid_rotation_plan(plan: dict) -> None:
    assert isinstance(plan, dict)
    assert "score" in plan
    assert isinstance(plan["score"], (int, float))
    assert "ease_adjusted_score" in plan
    assert isinstance(plan["ease_adjusted_score"], (int, float))

    easiness = plan.get("easiness_matrix")
    assert isinstance(easiness, dict)
    assert easiness

    timeline = plan.get("timeline")
    assert isinstance(timeline, dict)
    slots = timeline.get("slots")
    assert isinstance(slots, list)
    assert 3 <= len(slots) <= 4
    for slot in slots:
        assert isinstance(slot, dict)
        assert "crop_id" in slot
        assert "sowing_date" in slot
        assert "harvest_nominal_date" in slot
        stages = slot.get("stages")
        assert isinstance(stages, list) and len(stages) == 4
        for stage in stages:
            assert "start_date" in stage
            assert "end_date" in stage


def test_plan_global_rotations_uses_direct_pair_timeline_without_solve_trajectories():
    ds = load_snapshot(DEMO_SNAPSHOT)
    farm = Farm(
        country="LK",
        latitude=8.3114,
        longitude=80.4037,
        windows=(Window(4, 1, 7, 30),),
    )

    with (
        patch.object(
            rotation_engine,
            "build_direct_pair_timeline",
            wraps=timeline_adapter.build_direct_pair_timeline,
        ) as mock_direct,
        patch(
            "agroshift.rotation.timeline_core.solve_trajectories",
            side_effect=AssertionError("solve_trajectories must not be called by plan_global_rotations"),
        ),
    ):
        plans = plan_global_rotations(farm, ds, max_sequences=8)

    assert plans
    assert mock_direct.call_count > 0


def test_plan_global_rotations_season_free_and_legacy_modes():
    ds = load_snapshot(DEMO_SNAPSHOT)

    farm_single = Farm(
        country="LK",
        latitude=8.3114,
        longitude=80.4037,
        windows=(Window(4, 1, 7, 30),),
    )
    assert len(farm_single.windows) == 1
    plans_single = plan_global_rotations(farm_single, ds, max_sequences=8)
    assert len(plans_single) > 0
    for plan in plans_single:
        _assert_valid_rotation_plan(plan)

    farm_legacy = Farm(
        country="LK",
        latitude=8.3114,
        longitude=80.4037,
        windows=(Window(4, 1, 7, 30), Window(10, 1, 1, 20)),
    )
    assert len(farm_legacy.windows) == 2
    plans_legacy = plan_global_rotations(farm_legacy, ds, max_sequences=8)
    assert len(plans_legacy) > 0
    for plan in plans_legacy:
        _assert_valid_rotation_plan(plan)


def test_api_agronomy_rotations_season_free_start_date_payload():
    client = TestClient(app)
    resp = client.post(
        "/api/agronomy/rotations",
        json={
            "country": "LK",
            "latitude": 8.3114,
            "longitude": 80.4037,
            "start_date": "2026-04-01",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("mode") == "continuous"
    rotations = body.get("rotations")
    assert isinstance(rotations, list)
    assert len(rotations) > 0
    assert rotations[0]["overall_status"] in {"complementary", "conditional"}
    for plan in rotations:
        _assert_valid_rotation_plan(plan)


def test_api_agronomy_rotations_polygon_boundary_and_monitor_3d_start_date():
    client = TestClient(app)
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [80.4017, 8.3094],
                [80.4057, 8.3094],
                [80.4057, 8.3134],
                [80.4017, 8.3134],
                [80.4017, 8.3094],
            ]
        ],
    }

    r_rot = client.post(
        "/api/agronomy/rotations",
        json={
            "country": "LK",
            "boundary": polygon,
            "start_date": "2026-04-01",
            "offline": True,
            "max_sequences": 4,
        },
    )
    assert r_rot.status_code == 200, r_rot.text
    rot_body = r_rot.json()
    assert rot_body.get("mode") == "continuous"
    assert len(rot_body.get("rotations", [])) > 0

    r_3d = client.post(
        "/api/earth-data/monitor-3d",
        json={
            "country": "LK",
            "boundary": polygon,
            "start_date": "2026-04-01",
            "offline": True,
            "max_sequences": 4,
        },
    )
    assert r_3d.status_code == 200, r_3d.text
    mon_body = r_3d.json()
    assert "slab_3d" in mon_body
    plain = (mon_body.get("live_rotation_monitor") or {}).get("plain_rotations") or []
    assert len(plain) > 0


def test_api_agronomy_rotations_single_window_duration_payload():
    client = TestClient(app)
    resp = client.post(
        "/api/agronomy/rotations",
        json={
            "country": "LK",
            "latitude": 8.3114,
            "longitude": 80.4037,
            "windows": [{"start_month": 4, "duration_days": 120}],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("mode") == "continuous"
    rotations = body.get("rotations")
    assert isinstance(rotations, list)
    assert len(rotations) > 0
    assert rotations[0]["overall_status"] in {"complementary", "conditional"}
    for plan in rotations:
        _assert_valid_rotation_plan(plan)


def test_api_agronomy_rotations_polygon_boundary_and_monitor_3d_start_date():
    client = TestClient(app)
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [80.4017, 8.3094],
                [80.4057, 8.3094],
                [80.4057, 8.3134],
                [80.4017, 8.3134],
                [80.4017, 8.3094],
            ]
        ],
    }

    r_rot = client.post(
        "/api/agronomy/rotations",
        json={
            "country": "LK",
            "boundary": polygon,
            "start_date": "2026-04-01",
            "offline": True,
            "max_sequences": 4,
        },
    )
    assert r_rot.status_code == 200, r_rot.text
    rot_body = r_rot.json()
    assert rot_body.get("mode") == "continuous"
    assert len(rot_body.get("rotations", [])) > 0

    r_3d = client.post(
        "/api/earth-data/monitor-3d",
        json={
            "country": "LK",
            "boundary": polygon,
            "start_date": "2026-04-01",
            "offline": True,
            "max_sequences": 4,
        },
    )
    assert r_3d.status_code == 200, r_3d.text
    mon_body = r_3d.json()
    assert "slab_3d" in mon_body
    plain = (mon_body.get("live_rotation_monitor") or {}).get("plain_rotations") or []
    assert len(plain) > 0
