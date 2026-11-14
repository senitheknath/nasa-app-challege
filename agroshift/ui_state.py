"""UI draft state survives page navigation; never changes the scientific Farm contract."""

import calendar
import streamlit as st
from .climate import Window


def clear_wizard():
    for key in list(st.session_state):
        if key.startswith("wf_"):
            del st.session_state[key]


def capture():
    s = st.session_state
    d = s.setdefault("draft", {})
    water = s.get("wf_irrigation", d.get("irrigation", "unknown"))
    if d.get("irrigation") == "rainfed" and water != "rainfed":
        s["wf_irrigation_mm"] = None
    for field in (
        "drainage",
        "irrigation",
        "ph",
        "area_ha",
        "rain_fraction",
        "current",
        "previous",
        "pilot_confirmed",
        "mung_cultivar",
    ):
        key = "wf_" + field
        if key in s:
            d[field] = s[key]
    if "wf_farm_name" in s:
        s["farm_name"] = s["wf_farm_name"]
    if "wf_irrigation" in s:
        d["irrigation_mm"] = 0.0 if water == "rainfed" else s.get("wf_irrigation_mm")
        d["irrigation_basis"] = (
            "rain only"
            if water == "rainfed"
            else s.get("wf_irrigation_basis", "user supplied")
        )
    named = s.get("wf_season_name")
    if d.get("pilot_confirmed") and named in ("Yala then Maha", "Maha then Yala"):
        from .assistant import SEASON_TEMPLATES

        d["season_name"] = named
        d["windows"] = tuple(SEASON_TEMPLATES[named]["windows"])
    elif "wf_start_0" in s:
        windows = []
        for i in range(2 if d.get("pilot_confirmed") else 1):
            first, last = s.get(f"wf_start_{i}"), s.get(f"wf_end_{i}")
            windows.append(
                Window(first, 1, last, calendar.monthrange(2023, last)[1])
                if first and last
                else None
            )
        d["season_name"] = (
            "Choose my months" if d.get("pilot_confirmed") else "Farmer-selected months"
        )
        d["windows"] = tuple(windows)

    if "wf_include_baseline" in s:
        pair = tuple(s.get(f"wf_planned_{i}") for i in range(2))
        d["baseline"] = pair if s["wf_include_baseline"] and all(pair) else ()
