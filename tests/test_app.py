"""End-to-end farmer workflows through the normal Streamlit controls."""

from streamlit.testing.v1 import AppTest


def app():
    return AppTest.from_file("../app.py", default_timeout=35).run()


def click(a, label):
    next(b for b in a.button if b.label == label).click().run()
    assert not a.exception


def select(a, label, value):
    next(b for b in a.selectbox if b.label == label).set_value(value).run()
    assert not a.exception


def demo():
    a = app()
    click(a, "Try an example farm")
    assert a.session_state["page"] == "results"
    return a


def topic(a, name):
    if a.session_state["page"] != "research":
        click(a, "Explore")
    select(a, "Explore topic", name)


def test_full_recorded_demo_workflow():
    a = demo()
    assert len([b for b in a.button if b.label == "View details"]) <= 4
    click(a, "View details")
    assert a.expander and a.session_state["page"] == "details"
    click(a, "Back to results")
    click(a, "Compare")
    click(a, "Compare")
    click(a, "Compare selected (2)")
    assert len(a.multiselect[0].value) == 2
    click(a, "Back to results")
    topic(a, "Climate history")
    assert len(a.get("plotly_chart")) == 1
    topic(a, "What-if scenarios")
    assert a.dataframe
    topic(a, "Downloads")
    assert len(a.get("download_button")) == 5
    topic(a, "Learning lab")
    assert len(a.get("plotly_chart")) >= 4
    topic(a, "Ask about my results")
    a.text_input[0].input("What water evidence is missing?").run()
    assert not a.exception and any(
        "Water" in m.value or "water" in m.value for m in a.markdown
    )


def test_switching_farms_does_not_reuse_inputs_or_climate():
    a = demo()
    click(a, "Start another farm")
    assert (
        a.session_state["farm"] is None
        and a.session_state["dataset"] is None
        and not a.session_state["draft"]
    )
    select(a, "Country or territory", "KE")
    select(a, "Find your field", "Saved locations")
    select(a, "Location", "nairobi_kenya")
    click(a, "Use this location")
    assert a.session_state["dataset"].frame.attrs["latitude"] == -1.2921
    assert not a.session_state["demo_active"]


def test_empty_workflow_and_all_zero_weights():
    a = app()
    topic(a, "Rotation comparison")
    assert any("location" in n.value.lower() for n in a.info)
    click(a, "Use an example farm")
    topic(a, "Rotation comparison")
    for slider in a.slider:
        slider.set_value(0)
    a.run()
    assert not a.exception and any("priority" in n.value.lower() for n in a.warning)


def test_international_farmer_workflow_and_unknowns():
    a = app()
    click(a, "Analyze my farm")
    assert next(b for b in a.button if b.label == "Use this location").disabled
    select(a, "Country or territory", "KE")
    select(a, "Find your field", "Saved locations")
    select(a, "Location", "nairobi_kenya")
    click(a, "Use this location")
    click(a, "Continue")
    assert next(b for b in a.button if b.label == "Find crop options").disabled
    select(a, "Planting month", 3)
    select(a, "Last growing month", 7)
    select(a, "Last crop grown here", "wheat")
    click(a, "Find crop options")
    assert a.session_state["page"] == "results"
    f = a.session_state["farm"]
    assert (
        f.country == "KE"
        and len(f.windows) == 1
        and not f.baseline
        and f.current == "wheat"
    )
    assert (
        f.area_ha is None
        and f.ph is None
        and f.irrigation_mm is None
        and not f.pilot_confirmed
    )
    cards = a.session_state["cards"]
    assert cards and all(c["support"] == "general" for c in cards)
    assert len(a.get("download_button")) == 3


def test_regional_wizard_requires_confirmation_and_two_seasons():
    a = app()
    click(a, "Analyze my farm")
    select(a, "Country or territory", "LK")
    select(a, "Find your field", "Saved locations")
    select(a, "Location", "anuradhapura")
    click(a, "Use this location")
    a.checkbox[0].check().run()
    click(a, "Continue")
    select(a, "Growing seasons", "Yala then Maha")
    click(a, "Find crop options")
    assert a.session_state["farm"].pilot_confirmed and any(
        c["support"] == "regional" for c in a.session_state["cards"]
    )
    assert not any(
        r["baseline"]
        for r in __import__("agroshift.decision", fromlist=["assess"]).assess(
            a.session_state["dataset"].frame,
            a.session_state["farm"],
            a.session_state["weights"],
        )
    )


def test_map_country_check_rejects_open_ocean():
    from agroshift.locations import countries_at

    assert countries_at(0, 0) == set()
    assert "IN" in countries_at(30.901, 75.8573)
    assert "KE" in countries_at(-1.2921, 36.8219)


def test_provider_context_and_global_report_use_the_screened_cards():
    import json
    from agroshift.finder_report import make_record, readable

    a = demo()
    f = a.session_state["farm"]
    topic(a, "Data sources")
    select(a, "Look up", "Soil estimate")
    # The verified offline estimate is already available during field setup.
    from agroshift.providers import soil_context

    soil = soil_context(f.latitude, f.longitude, offline=True)
    assert soil["value"] == 5.8 and f.ph == 6.5
    record = make_record(
        a.session_state["dataset"],
        f,
        a.session_state["cards"],
        a.session_state["weights"],
    )
    raw = readable(record)
    assert record["options"] == a.session_state["cards"]
    assert all(r["name"] in raw for r in record["options"])
    assert "fictional" in raw and record["farm"]["ph"] == 6.5
    assert "success_probability" not in json.dumps(record)


def test_turning_on_irrigation_leaves_amount_unknown():
    a = demo()
    click(a, "Edit my field")
    select(a, "Where does your water come from?", "reliable")
    assert (
        next(
            n for n in a.number_input if n.label == "Net irrigation per season (mm)"
        ).value
        is None
    )
    click(a, "Continue")
    click(a, "Find crop options")
    assert a.session_state["farm"].irrigation == "reliable"
    assert a.session_state["farm"].irrigation_mm is None


def test_returning_to_season_preserves_months_and_history():
    a = app()
    click(a, "Analyze my farm")
    select(a, "Country or territory", "KE")
    select(a, "Find your field", "Saved locations")
    select(a, "Location", "nairobi_kenya")
    click(a, "Use this location")
    click(a, "Continue")
    select(a, "Planting month", 1)
    select(a, "Last growing month", 12)
    select(a, "Last crop grown here", "cassava")
    click(a, "Back")
    click(a, "Continue")
    assert next(s for s in a.selectbox if s.label == "Planting month").value == 1
    assert next(s for s in a.selectbox if s.label == "Last growing month").value == 12
    assert (
        next(s for s in a.selectbox if s.label == "Last crop grown here").value
        == "cassava"
    )
    click(a, "Find crop options")
    assert a.session_state["page"] == "results"
