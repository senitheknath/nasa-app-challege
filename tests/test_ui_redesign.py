"""Behavioral regressions for form drafts, comparison, outages and bounded catalogue queries."""

from unittest.mock import Mock
from contextlib import closing
import json
import pytest

from agroshift import knowledge, knowledge_store
from test_app import app, demo, click, select, topic


def test_draft_survives_primary_navigation_without_running_an_assessment(monkeypatch):
    from agroshift import screening, finder_ui

    a = app()
    click(a, "Analyze my farm")
    select(a, "Country or territory", "KE")
    assert (
        next(s for s in a.selectbox if s.label == "Find your field").value
        == "Search by name"
    )
    select(a, "Find your field", "Saved locations")
    select(a, "Location", "nairobi_kenya")
    click(a, "Use this location")
    history = Mock(
        side_effect=AssertionError("Navigation must reuse the loaded weather")
    )
    engine = Mock(side_effect=AssertionError("Navigation must not assess a draft"))
    monkeypatch.setattr(finder_ui, "load_history", history)
    monkeypatch.setattr(screening, "find_options", engine)
    a.text_input(key="wf_farm_name").input("River field").run()
    a.number_input(key="wf_ph").set_value(6.2).run()
    select(a, "Where does your water come from?", "reliable")
    click(a, "Dashboard")
    click(a, "Continue farm setup")
    assert a.text_input(key="wf_farm_name").value == "River field"
    assert a.number_input(key="wf_ph").value == 6.2
    assert a.number_input(key="wf_irrigation_mm").value is None
    click(a, "Continue")
    select(a, "Planting month", 3)
    select(a, "Last growing month", 7)
    click(a, "Explore")
    click(a, "Dashboard")
    click(a, "Continue farm setup")
    assert a.selectbox(key="wf_start_0").value == 3
    assert a.selectbox(key="wf_end_0").value == 7
    assert a.session_state["draft"]["ph"] == 6.2
    assert a.session_state["farm"] is None
    history.assert_not_called()
    engine.assert_not_called()


def test_comparison_selection_survives_details_and_main_navigation(monkeypatch):
    from agroshift import screening, finder_ui

    a = demo()
    cards = a.session_state["cards"]
    monkeypatch.setattr(
        screening,
        "find_options",
        Mock(side_effect=AssertionError("Unexpected reassessment")),
    )
    monkeypatch.setattr(
        finder_ui,
        "load_history",
        Mock(side_effect=AssertionError("Unexpected weather request")),
    )
    click(a, "Compare")
    click(a, "Compare")
    ids = list(a.session_state["comparison_ids"])
    assert len(ids) == 2
    click(a, "Compare selected (2)")
    click(a, "View details")
    click(a, "Back to comparison")
    assert a.multiselect[0].value == ids
    click(a, "Dashboard")
    click(a, "Recommendations")
    assert a.session_state["comparison_ids"] == ids
    assert a.session_state["cards"] == cards
    click(a, "Compare selected (2)")
    a.multiselect[0].set_value([cards[1]["id"], cards[2]["id"], cards[3]["id"]]).run()
    selected = a.multiselect[0].value
    click(a, "Back to results")
    assert a.session_state["comparison_ids"] == selected


def test_rain_only_to_irrigated_never_restores_an_old_amount():
    a = demo()
    click(a, "Edit my field")
    select(a, "Where does your water come from?", "reliable")
    a.number_input(key="wf_irrigation_mm").set_value(120.0).run()
    select(a, "Where does your water come from?", "rainfed")
    click(a, "Dashboard")
    click(a, "Continue farm setup")
    select(a, "Where does your water come from?", "supplemental")
    assert a.number_input(key="wf_irrigation_mm").value is None
    assert a.session_state["draft"]["irrigation_mm"] is None


def test_factor_labels_do_not_claim_unknown_inputs_are_suitable():
    from agroshift.ui_components import factors

    value = {"assessed": ["historical temperature"], "water": "Not assessed"}
    result = dict(factors(value))
    assert result == {
        "Temperature": "Historical record checked",
        "Soil": "Not assessed",
        "Water": "Not assessed",
    }
    assert all("range" not in text and "%" not in text for text in result.values())


def test_category_filter_is_real_bounded_and_combined_with_name(monkeypatch, tmp_path):
    monkeypatch.delenv("AGROSHIFT_DATABASE_URL", raising=False)
    monkeypatch.setenv("AGROSHIFT_KNOWLEDGE_PATH", str(tmp_path / "catalogue.sqlite3"))
    knowledge.clear_cache()
    categories = knowledge.crop_categories()
    assert "Cereals" in categories
    total = knowledge.count_crops(category="Cereals")
    rows = knowledge.search_crops(category="Cereals", limit=2)
    assert (
        total >= 2
        and len(rows) == 2
        and all(r["group_name"] == "Cereals" for r in rows)
    )
    assert knowledge.search_crops("maize", category="Cereals")[0]["id"] == "maize"
    assert knowledge.count_crops("maize", category="does not exist") == 0
    assert knowledge.search_crops(category="Cereals", offset=total) == []
    knowledge.clear_cache()


def test_legacy_checksum_exception_accepts_only_exact_packaging_variant(
    tmp_path, monkeypatch
):
    aliases = json.loads(
        (knowledge_store.ROOT / "db/migration_compatibility.json").read_text()
    )
    name = "005_search_tokens.sql"
    with closing(
        knowledge_store.sqlite_connect(tmp_path / "migration.sqlite3")
    ) as conn:
        knowledge_store.migrate(conn)
        conn.execute(
            "UPDATE ag_schema_version SET digest=? WHERE name=?",
            (aliases[name]["legacy"], name),
        )
        knowledge_store.migrate(conn)
        assert (
            conn.execute(
                "SELECT digest FROM ag_schema_version WHERE name=?", (name,)
            ).fetchone()[0]
            == aliases[name]["legacy"]
        )
        modified = tmp_path / "migrations"
        modified.mkdir()
        for p in knowledge_store.MIGRATIONS.glob("*.sql"):
            (modified / p.name).write_text(
                p.read_text() + ("\n-- Unrecognized edit\n" if p.name == name else "")
            )
        monkeypatch.setattr(knowledge_store, "MIGRATIONS", modified)
        with pytest.raises(ValueError, match="changed after application"):
            knowledge_store.migrate(conn)


def test_automated_site_insights_and_one_click_season_suggestion():
    from agroshift.climate_insights import site_summary, suggest_window
    from agroshift.ui_components import build_climograph_figure

    a = app()
    click(a, "Analyze my farm")
    select(a, "Country or territory", "KE")
    select(a, "Find your field", "Saved locations")
    select(a, "Location", "nairobi_kenya")
    click(a, "Use this location")
    ds = a.session_state["dataset"]
    summary = site_summary(ds)
    assert summary["annual_rain_mm"] > 500
    assert summary["annual_et0_mm"] > 800
    suggestion = suggest_window(summary["climatology"], summary["growing_period"])
    assert suggestion and 1 <= suggestion["start_month"] <= 12
    click(a, "Continue")
    # Before clicking suggestion, months are unset and Find crop options is disabled.
    assert next(b for b in a.button if b.label == "Find crop options").disabled
    a.button(key="apply_suggested_season").click().run()
    assert not a.exception
    assert a.selectbox(key="wf_start_0").value == suggestion["start_month"]
    assert a.selectbox(key="wf_end_0").value == suggestion["end_month"]
    assert not next(b for b in a.button if b.label == "Find crop options").disabled
    fig = build_climograph_figure(ds)
    assert len(fig.data) >= 4


def test_next_gen_intelligent_visual_and_agronomic_features():
    from agroshift.climate_insights import (
        crop_12month_sowing_matrix,
        crop_stage_water_demand,
        previous_crop_rotation_badge,
        seasonal_weather_risk_summary,
    )

    a = demo()
    ds = a.session_state["dataset"]
    f = a.session_state["farm"]
    cards = a.session_state["cards"]

    # 1. Seasonal weather extremes & decadal shift summary
    risk = seasonal_weather_risk_summary(ds, f.windows[0])
    assert risk and risk["seasons_evaluated"] >= 20
    assert risk["median_dry_spell_days"] >= 0
    assert risk["warming_delta_c"] is not None

    # 2. 12-month × multi-crop sowing heatmap matrix
    matrix = crop_12month_sowing_matrix(ds, cards, max_crops=6)
    assert matrix and len(matrix["rows"]) == 6
    assert all(len(row["cells"]) == 12 for row in matrix["rows"])

    # 3. 4-Stage FAO-56 crop water demand (ETc = Kc × ET0)
    stages = crop_stage_water_demand("maize", ds, f.windows[0])
    assert len(stages) == 4
    assert stages[2]["stage_key"] == "mid_season" and stages[2]["etc_mm"] > 0

    # 4. Botanical rotation badges for previous crop
    rot_legume = previous_crop_rotation_badge("rice", "cowpea")
    assert rot_legume and rot_legume["kind"] == "legume_benefit"
    rot_same = previous_crop_rotation_badge("rice", "maize")
    assert rot_same and rot_same["kind"] == "caution"

    # 5. One-click suggested farmer question in Ask about my results
    topic(a, "Ask about my results")
    a.button(key="suggest_q_0").click().run()
    assert not a.exception
    assert any("Water" in m.value or "water" in m.value for m in a.markdown)


