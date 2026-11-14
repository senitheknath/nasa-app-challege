"""Farm files, identity boundaries, uncertainty and the ordinary farmer workflow."""

from copy import deepcopy
from dataclasses import asdict
import json
import pytest
from agroshift.assistant import DEMO_SCENARIOS
from agroshift.farm_records import (
    profile,
    read_profile,
    farm_from_dict,
    boundary_polygon,
)
from agroshift.private_store import owner_from_claims
from agroshift.power import DataError


@pytest.fixture
def farm():
    return DEMO_SCENARIOS["scenario_1_well_drained"]["farm"]


def test_farm_roundtrip_keeps_unknowns_and_source(farm):
    value = profile("North field", farm, "Anuradhapura")
    loaded = read_profile(json.dumps(value).encode())
    assert farm_from_dict(loaded["farm"]) == farm
    broken = deepcopy(value)
    broken["farm"]["latitude"] = False
    with pytest.raises(DataError):
        read_profile(json.dumps(broken).encode())
    broken = deepcopy(value)
    broken["farm"]["ph"] = float("nan")
    with pytest.raises(DataError):
        read_profile(json.dumps(broken).encode())
    broken = deepcopy(value)
    broken["farm"]["windows"][0]["start_month"] = 14
    with pytest.raises(DataError):
        read_profile(json.dumps(broken).encode())
    with pytest.raises(DataError):
        read_profile(b" " * 100001)
    broken = deepcopy(value)
    broken["name"] = None
    with pytest.raises(DataError):
        read_profile(json.dumps(broken).encode())
    broken = deepcopy(value)
    broken["owner_id"] = "not-trusted"
    with pytest.raises(DataError):
        read_profile(json.dumps(broken).encode())


def test_boundary_rejects_crossings_wrong_location_and_degenerate_polygons(farm):
    x, y = farm.longitude, farm.latitude
    good = {
        "type": "Polygon",
        "coordinates": [
            [
                [x - 0.01, y - 0.01],
                [x + 0.01, y - 0.01],
                [x + 0.01, y + 0.01],
                [x - 0.01, y + 0.01],
                [x - 0.01, y - 0.01],
            ]
        ],
    }
    assert boundary_polygon(good, farm) == good
    wrong = deepcopy(good)
    wrong["coordinates"][0] = [[a + 2, b] for a, b in wrong["coordinates"][0]]
    crossed = deepcopy(good)
    crossed["coordinates"][0][1], crossed["coordinates"][0][2] = (
        crossed["coordinates"][0][2],
        crossed["coordinates"][0][1],
    )
    degenerate = {
        "type": "Polygon",
        "coordinates": [[[x, y], [x + 0.01, y], [x + 0.02, y], [x, y]]],
    }
    for value in (wrong, crossed, degenerate, {"type": "Point", "coordinates": [x, y]}):
        with pytest.raises(DataError):
            boundary_polygon(value, farm)


def test_identity_is_issuer_bound_and_requires_unexpired_verified_claims():
    claims = dict(is_logged_in=True, iss="https://issuer.example", sub="alice", exp=200)
    owner = owner_from_claims(claims, claims["iss"], now=100)
    assert owner == owner_from_claims(
        dict(claims, email="a@example.org"), claims["iss"], now=100
    )
    assert owner != owner_from_claims(dict(claims, sub="bob"), claims["iss"], now=100)
    for bad in (
        dict(claims, is_logged_in=False),
        dict(claims, exp=100),
        dict(claims, exp=None),
        dict(claims, exp=float("nan")),
        dict(claims, sub=""),
    ):
        with pytest.raises(DataError):
            owner_from_claims(bad, claims["iss"], now=100)
    with pytest.raises(DataError):
        owner_from_claims(claims, "https://another.example", now=100)


def test_two_saved_farms_and_history_are_session_isolated(monkeypatch):
    monkeypatch.setenv("AGROSHIFT_CONTEXT_OFFLINE", "1")
    from test_app import demo, app, click, select

    a = demo()
    click(a, "Save this farm")
    next(t for t in a.text_input if t.label == "Farm name").input("North field").run()
    click(a, "Save farm")
    first = a.session_state["active_farm_id"]
    click(a, "Save farm")
    assert len(a.session_state["session_history"][first]) == 1
    click(a, "Add a farm")
    select(a, "Country or territory", "KE")
    select(a, "Find your field", "Saved locations")
    select(a, "Location", "nairobi_kenya")
    click(a, "Use this location")
    assert a.session_state["context"]["point"] == ["KE", -1.2921, 36.8219]
    click(a, "Continue")
    select(a, "Planting month", 3)
    select(a, "Last growing month", 7)
    click(a, "Find crop options")
    click(a, "Save this farm")
    next(t for t in a.text_input if t.label == "Farm name").input("Kenya field").run()
    click(a, "Save farm")
    assert len(a.session_state["session_farms"]) == 2
    a.button(key="open_farm_" + first).click().run()
    assert not a.exception
    assert a.session_state["farm"].country == "LK" and a.session_state["farm"].ph == 6.5
    assert a.session_state["active_farm_id"] == first
    click(a, "Dashboard")
    assert any("North field" in t.value for t in a.subheader)
    assert not app().session_state["session_farms"]


def test_automatic_context_failure_stays_separate(monkeypatch):
    from agroshift import farm_context
    from agroshift.providers import soil_context

    farm_context._fetch.cache_clear()
    monkeypatch.setattr(
        farm_context.providers,
        "soil_context",
        lambda *a, **k: {"status": "verified", "value": 5.8, "kind": "modelled"},
    )
    monkeypatch.setattr(
        farm_context.providers,
        "calendar_crops",
        lambda *a, **k: (_ for _ in ()).throw(TimeoutError()),
    )
    context = farm_context.location_context("LK", 8.3114, 80.4037)
    assert context["soil"]["value"] == 5.8 and context["calendar"]["value"] is None
    assert "farm" not in context
    farm_context._fetch.cache_clear()


def test_capabilities_and_report_preserve_missing_factors(monkeypatch):
    monkeypatch.setenv("AGROSHIFT_CONTEXT_OFFLINE", "1")
    from test_app import demo
    from agroshift.finder_report import make_record, readable

    a = demo()
    r = make_record(
        a.session_state["dataset"],
        a.session_state["farm"],
        a.session_state["cards"],
        a.session_state["weights"],
        a.session_state["context"],
    )
    assert (
        r["capabilities"]["C"]["available"] and not r["capabilities"]["D"]["available"]
    )
    assert r["reference_versions"] and all(c["unknown"] for c in r["options"])
    assert r["environmental_context"]["soil"]["kind"] == "modelled"
    assert "Still unknown:" in readable(r)
