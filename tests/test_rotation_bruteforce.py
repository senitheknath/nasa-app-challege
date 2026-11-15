"""Verification tests for brute-force rotation planning and season-free API payloads."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from agroshift.climate import Window
from agroshift.decision import Farm
from agroshift.power import load_snapshot
from agroshift.rotation import CropProfile, RotationConfig, engine as rotation_engine
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


def test_rotation_config_expiry_buffer_days_clamping_and_validation():
    assert RotationConfig().expiry_buffer_days == 7
    assert RotationConfig(expiry_buffer_days=-10).expiry_buffer_days == 0
    assert RotationConfig(expiry_buffer_days=99).expiry_buffer_days == 35
    assert RotationConfig(expiry_buffer_days=14).expiry_buffer_days == 14

    try:
        RotationConfig(expiry_buffer_days=True)  # type: ignore[arg-type]
        raise AssertionError("Expected ValueError for bool expiry_buffer_days")
    except ValueError:
        pass


def test_build_direct_pair_timeline_respects_expiry_buffer_days():
    p1 = CropProfile(
        id="wide_c1",
        name="Wide C1",
        family="Poaceae",
        traits={"indicative_cycle_duration": {"low": 90, "high": 140}},
    )
    p2 = CropProfile(
        id="pea",
        name="Pea",
        family="Fabaceae",
        is_nitrogen_fixer=True,
        traits={"indicative_cycle_duration": {"low": 80, "high": 100}},
    )
    w1 = Window(4, 1, 7, 30)
    w2 = Window(10, 1, 1, 20)
    s1_card = {"status": "possible"}
    s2_card = {"status": "possible"}
    trans = {"status": "complementary"}

    tl_flex = timeline_adapter.build_direct_pair_timeline(
        p1,
        p2,
        w1,
        w2,
        s1_card,
        s2_card,
        trans,
        continuous=True,
        config=RotationConfig(expiry_buffer_days=3),
    )
    tl_default = timeline_adapter.build_direct_pair_timeline(
        p1,
        p2,
        w1,
        w2,
        s1_card,
        s2_card,
        trans,
        continuous=True,
    )
    tl_strict = timeline_adapter.build_direct_pair_timeline(
        p1,
        p2,
        w1,
        w2,
        s1_card,
        s2_card,
        trans,
        continuous=True,
        expiry_buffer_days=21,
    )

    assert tl_flex["days_until_hard_expiry"] > tl_default["days_until_hard_expiry"]
    assert tl_default["days_until_hard_expiry"] - tl_strict["days_until_hard_expiry"] == 14
    assert tl_default["days_until_safe_expiry"] - tl_strict["days_until_safe_expiry"] == 14
    assert tl_strict["collision_probability_pct"] > tl_default["collision_probability_pct"]
    assert tl_strict["feasible"] is False
    assert tl_strict["turnaround_summary"]["status"] == "tight"


def test_extend_timeline_with_followup_crops_computes_slot3_collision_and_uses_buffer():
    p1 = CropProfile(
        id="c1",
        name="Crop 1",
        family="Poaceae",
        traits={"indicative_cycle_duration": {"low": 90, "high": 110}},
    )
    p2 = CropProfile(
        id="c2",
        name="Crop 2",
        family="Fabaceae",
        is_nitrogen_fixer=True,
        traits={"indicative_cycle_duration": {"low": 80, "high": 100}},
    )
    # Duration bounds: min=80, nom=110, max=140 -> span=60, (d_max - d_nom)=30
    p3 = CropProfile(
        id="c3",
        name="Crop 3",
        family="Brassicaceae",
        traits={"indicative_cycle_duration": {"low": 80, "high": 140}},
    )
    p4 = CropProfile(
        id="c4",
        name="Crop 4",
        family="Apiaceae",
        traits={"indicative_cycle_duration": {"low": 75, "high": 95}},
    )
    profiles = {"c1": p1, "c2": p2, "c3": p3, "c4": p4}
    cards = {cid: {"status": "possible"} for cid in profiles}

    w1 = Window(4, 1, 7, 30)
    w2 = Window(10, 1, 1, 20)
    base_tl = timeline_adapter.build_direct_pair_timeline(
        p1,
        p2,
        w1,
        w2,
        cards["c1"],
        cards["c2"],
        {"status": "complementary"},
        continuous=True,
        config=RotationConfig(expiry_buffer_days=14),
    )

    rotation_engine._extend_timeline_with_followup_crops(
        base_tl,
        c1_id="c1",
        c2_id="c2",
        follow_pool=["c3", "c4"],
        profiles=profiles,
        cards_s1=cards,
        cards_s2=cards,
        target_slots=4,
        config=RotationConfig(expiry_buffer_days=14),
    )

    slots = base_tl["slots"]
    assert len(slots) == 4
    slot3 = slots[2]
    slot4 = slots[3]

    # For Slot 3 (!is_last): turnaround=14, buffer=14, slack window=21
    # deadline = start + 110 + 14 + 21 - 14 = start + 131
    # hard_expiry = deadline - 110 = start + 21; safe_expiry = deadline - 140 = start - 9
    # end_min = start + 80, end_max = start + 140, span = 60 => (140 - 131) / 60 * 100 = 15.0%
    assert slot3["collision_probability_pct"] == 15.0
    assert slot3["days_until_hard_expiry"] == 21
    assert slot3["days_until_safe_expiry"] == -9
    assert slot4["collision_probability_pct"] == 0.0


def test_api_agronomy_rotations_accepts_and_applies_expiry_buffer_days():
    client = TestClient(app)
    base_payload = {
        "country": "LK",
        "latitude": 8.3114,
        "longitude": 80.4037,
        "start_date": "2026-04-01",
        "max_sequences": 4,
        "candidate_crop_ids": ["maize", "mung_bean", "rice"],
    }

    r_default = client.post("/api/agronomy/rotations", json=base_payload)
    assert r_default.status_code == 200, r_default.text
    b_default = r_default.json()
    assert b_default["threshold_config"] == {"expiry_buffer_days": 7}

    r_strict = client.post(
        "/api/agronomy/rotations",
        json={**base_payload, "expiry_buffer_days": 21},
    )
    assert r_strict.status_code == 200, r_strict.text
    b_strict = r_strict.json()
    assert b_strict["threshold_config"] == {"expiry_buffer_days": 21}

    by_id_default = {p["id"]: p for p in b_default["rotations"]}
    by_id_strict = {p["id"]: p for p in b_strict["rotations"]}
    common_ids = set(by_id_default) & set(by_id_strict)
    assert common_ids
    pid = sorted(common_ids)[0]
    assert (
        by_id_default[pid]["timeline"]["days_until_hard_expiry"]
        - by_id_strict[pid]["timeline"]["days_until_hard_expiry"]
        == 14
    )

    r_clamped = client.post(
        "/api/agronomy/rotations",
        json={**base_payload, "expiry_buffer_days": 100},
    )
    assert r_clamped.status_code == 200, r_clamped.text
    assert r_clamped.json()["threshold_config"] == {"expiry_buffer_days": 35}

    r_invalid = client.post(
        "/api/agronomy/rotations",
        json={**base_payload, "expiry_buffer_days": True},
    )
    assert r_invalid.status_code == 400
