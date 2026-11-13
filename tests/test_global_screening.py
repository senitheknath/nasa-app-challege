from dataclasses import replace
from datetime import date
import csv
from pathlib import Path

import pytest

from agroshift.climate import Window
from agroshift.decision import Farm
from agroshift.knowledge import global_traits, search_crops
from agroshift.power import DataError, archived_history, request_parameters
from agroshift.screening import find_options, region_evidence

ROOT = Path(__file__).resolve().parents[1]
HUBS = list(csv.DictReader((ROOT / "data/global_nasa_stations_summary.csv").read_text().splitlines()))


def archived_farm(country):
    row = next(r for r in HUBS if r["country"] == country)
    lat, lon = float(row["latitude"]), float(row["longitude"])
    series = archived_history(request_parameters(lat, lon, date(2001, 1, 1), date(2025, 12, 31)))
    assert series.provenance["sha256"] == row["sha256"]
    return Farm(country=country, latitude=lat, longitude=lon), series


@pytest.mark.parametrize("country", ["LK", "IN", "KE", "BR", "US", "AU"])
def test_real_archives_support_general_but_no_unconfirmed_rotation(country):
    farm, history = archived_farm(country)
    options = find_options(farm, history)
    assert region_evidence(country)["sources"]
    assert len(options) >= 10
    assert all(o["support"] == "general" and o["sources"] for o in options)
    assert any(o["id"] == "wheat" for o in options)
    # Crops without global traits are withheld everywhere in general mode; rice & mung_bean are now global.
    assert {"cowpea", "yam"}.isdisjoint(o["id"] for o in options)
    assert {"rice", "mung_bean"}.issubset(o["id"] for o in options)
    assert all("yield" not in " ".join((c["summary"], c["reason"], c["water"])).lower() for c in options)
    assert all("probability" not in c and "expected_yield" not in c for c in options)


def test_terms_do_not_confer_agronomic_support():
    assert search_crops("berenjena")[0]["id"] == "eggplant"
    assert search_crops("frijol mungo")[0]["id"] == "mung_bean"
    assert search_crops("lens culinaris")[0]["id"] == "lentil"
    missing = search_crops("pigeon pea")[0]
    assert missing["support_level"] == "catalogue"
    assert missing["concept_uri"].startswith("http://aims.fao.org/")
    assert any(t["source_url"].startswith("https://www.fao.org/") for t in global_traits())


def test_material_constraints_and_missing_inputs():
    farm, data = archived_farm("KE")
    clean = {c["id"]: c for c in find_options(farm, data)}
    assert clean["cassava"]["status"] == "unknown"
    assert clean["tomato"]["water"] != "Water is adequate."
    wet = {c["id"]: c for c in find_options(replace(farm, drainage="waterlogged", ph=8.2), data)}
    assert wet["tomato"]["status"] == "blocked"
    assert wet["cassava"]["status"] == "outside"
    assert any("8.2" in line for line in wet["cassava"]["details"])
    assert not any("8.2" in line for line in clean["cassava"]["details"])


def test_reference_scope_and_weather_provenance():
    farm, series = archived_farm("US")
    with pytest.raises(DataError, match="coordinates"):
        find_options(replace(farm, latitude=farm.latitude + 0.1), series)
    with pytest.raises(DataError, match="verified NASA"):
        find_options(farm, replace(series, provenance={**series.provenance, "simulated": True}))
    short = replace(series, frame=series.frame.iloc[:365])
    wheat = next(c for c in find_options(farm, short) if c["id"] == "wheat")
    assert not any("typical day was" in text for text in wheat["details"])
    assert any("10 seasons" in text for text in wheat["details"])


def test_regionally_blocked_crops_cannot_return_as_general_matches():
    farm, series = archived_farm("LK")
    options = find_options(replace(farm, pilot_confirmed=True, drainage="waterlogged"), series)
    assert len(options) == len(set(c["id"] for c in options))
    for crop in ("maize", "groundnut", "cowpea", "mung_bean"):
        card = next(c for c in options if c["id"] == crop)
        assert card["support"] == "regional" and card["status"] == "blocked"
    assert next(c for c in options if c["id"] == "rice")["support"] == "regional"


def test_water_requires_usable_rain_and_matching_cycle():
    farm, data = archived_farm("BR")
    farm = replace(farm, windows=(Window(1, 1, 5, 10), Window(8, 1, 10, 31)), irrigation="reliable")
    def crop(f):
        return next(c for c in find_options(f, data) if c["id"] == "barley")
    assert "Estimated supply" not in crop(farm)["water"]
    assert "Estimated supply" not in crop(replace(farm, rain_fraction=.5))["water"]
    assert "Estimated supply" in crop(replace(farm, rain_fraction=.5, irrigation_mm=85))["water"]
    short_window = replace(farm, rain_fraction=1, irrigation_mm=1000,
                           windows=(Window(1, 1, 2, 28), Window(8, 1, 10, 31)))
    assert "full growing cycle" in crop(short_window)["water"]


def test_one_window_does_not_imply_a_rotation():
    farm, series = archived_farm("LK")
    chosen = replace(farm, windows=(Window(6, 1, 9, 30),), pilot_confirmed=True)
    options = find_options(chosen, series)
    assert options and all(c["support"] == "general" for c in options)
    with pytest.raises(DataError, match="no weather history"):
        find_options(chosen, None)


def test_global_temperature_and_rain_coverage_are_independent():
    farm, data = archived_farm("KE")
    altered = data.frame.copy()
    altered.loc[(altered.index.month == 5) & (altered.index.day == 1), "T2M"] = float("nan")
    options = find_options(replace(farm, ph=5.8), replace(data, frame=altered))
    wheat = next(c for c in options if c["id"] == "wheat")
    assert not any("The typical day was" in line for line in wheat["details"])
    cassava = next(c for c in options if c["id"] == "cassava")
    assert cassava["status"] == "possible"
    assert "pH" in cassava["reason"]
