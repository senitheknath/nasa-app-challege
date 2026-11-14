"""Shared presentation and agricultural visual components. Scientific values are never recomputed here."""

import calendar
from html import escape
import json
import streamlit as st

STATUS = {
    "possible": "Worth considering",
    "check": "Check before planting",
    "outside": "Outside reference range",
    "blocked": "Does not fit reported conditions",
    "unknown": "Not enough information",
}
STATUS_ICON = {
    "possible": "●",
    "check": "▲",
    "outside": "◆",
    "blocked": "✕",
    "unknown": "○",
}
SUPPORT = {
    "general": "General crop reference",
    "regional": "Regional crop reference",
    "catalogue": "Catalogue only",
}
UNKNOWN = {
    "temperature fit": "temperature",
    "soil pH fit": "soil pH",
    "drainage fit": "drainage",
    "water adequacy": "water supply",
    "water fit": "water supply",
    "soil fit": "soil conditions",
    "local variety and pests": "local variety and pests",
    "local pests and field performance": "pests and field performance",
}
ASSESSED = {
    "temperature": "Historical temperature",
    "soil": "Soil conditions",
    "water": "Approximate water supply",
    "historical temperature": "Historical temperature",
    "measured soil pH": "Measured soil pH",
    "reported drainage": "Reported drainage",
    "approximate seasonal water supply": "Approximate water supply",
}

CROP_ICONS = {
    "cereal": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 21V5"/><path d="M12 8c-3 0-5-2-5-4 3 0 5 2 5 4Z"/><path d="M12 8c3 0 5-2 5-4-3 0-5 2-5 4Z"/>'
        '<path d="M12 13c-3 0-5-2-5-4 3 0 5 2 5 4Z"/><path d="M12 13c3 0 5-2 5-4-3 0-5 2-5 4Z"/>'
        '<path d="M12 18c-3 0-5-2-5-4 3 0 5 2 5 4Z"/><path d="M12 18c3 0 5-2 5-4-3 0-5 2-5 4Z"/></svg>'
    ),
    "legume": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M6 18c5 2 12-5 12-12-7 0-14 7-12 12Z"/><circle cx="10" cy="14" r="1.3"/><circle cx="13" cy="11" r="1.3"/><circle cx="15.5" cy="8.5" r="1.1"/></svg>'
    ),
    "root": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M9 3c1 2 2 3 3 3s2-1 3-3"/><path d="M12 6c-4 0-6 3-5 8 1 4 3 7 5 7s4-3 5-7c1-5-1-8-5-8Z"/><path d="M10 12h4"/><path d="M10.5 16h3"/></svg>'
    ),
    "oilseed": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M19.1 4.9 17 7M7 17l-2.1 2.1"/></svg>'
    ),
    "vegetable": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 6c-4.5 0-8 3.2-8 7.5S7.5 21 12 21s8-3.2 8-7.5S16.5 6 12 6Z"/><path d="M10 6c0-2 1-3 2-3s2 1 2 3"/><path d="M8 6l4 2 4-2"/></svg>'
    ),
    "fruit": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 7c-4 0-7 3-7 7 0 4.2 3 7 7 7s7-2.8 7-7c0-4-3-7-7-7Z"/><path d="M12 7V3"/><path d="M12 4c2-1 4-1 5 1-2 1-3 1-5-1Z"/></svg>'
    ),
    "leaf": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.4 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/><path d="M2 21c0-3 1.8-5.4 5.1-6 3.5-.6 6.9-2 8.9-5"/></svg>'
    ),
}

GAEZ_SCALE = [
    ("Very high", "#007000", "#FFFFFF"),
    ("High", "#15AE11", "#FFFFFF"),
    ("Good", "#ACE15E", "#1B2A21"),
    ("Medium", "#FED801", "#1B2A21"),
    ("Moderate", "#CE9D53", "#1B2A21"),
    ("Marginal", "#CD6C01", "#FFFFFF"),
    ("Very marginal", "#808080", "#FFFFFF"),
    ("Not suitable", "#CFCFCF", "#1B2A21"),
]


def crop_group_kind(group_name: str | None = None, crop_id: str | None = None) -> str:
    g = (group_name or "").lower()
    cid = (crop_id or "").lower()
    if "cereal" in g or cid in ("maize", "wheat", "rice", "sorghum", "barley", "pearl_millet", "finger_millet", "oats", "rye"):
        return "cereal"
    if "pulse" in g or "legum" in g or cid in ("cowpea", "mung_bean", "mungbean", "groundnut", "soybean", "chickpea", "lentil", "pigeon_pea", "common_bean", "faba_bean", "pea"):
        return "legume"
    if "root" in g or "tuber" in g or cid in ("cassava", "potato", "sweet_potato", "yam", "taro", "sugar_beet"):
        return "root"
    if "oil" in g or cid in ("sunflower", "sesame", "rapeseed", "mustard", "safflower", "castor", "linseed"):
        return "oilseed"
    if "vegetable" in g or "melon" in g or cid in ("tomato", "onion", "cabbage", "eggplant", "chili_pepper", "okra", "cucumber", "pumpkin", "carrot", "garlic"):
        return "vegetable"
    if "fruit" in g or "nut" in g or cid in ("banana", "mango", "papaya", "pineapple", "avocado", "citrus", "coconut"):
        return "fruit"
    return "leaf"


def crop_icon(group_name: str | None = None, crop_id: str | None = None) -> str:
    return CROP_ICONS[crop_group_kind(group_name, crop_id)]


def page_heading(title, description=None):
    st.title(title, anchor=False)
    if description:
        caption(description)


def caption(text):
    st.html('<p class="as-caption">' + escape(str(text)) + "</p>")


def context_bar(items):
    body = "".join(
        f"<div><dt>{escape(str(k))}</dt><dd>{escape(str(v))}</dd></div>"
        for k, v in items
    )
    st.html('<dl class="as-context">' + body + "</dl>")


def badge(card):
    st_key = card["status"]
    icon = STATUS_ICON.get(st_key, "○")
    return (
        f'<span class="as-status as-status-{escape(st_key)}">'
        f'<span aria-hidden="true">{icon}</span> {escape(STATUS[st_key])}</span>'
    )


def factors(card):
    assessed = card.get("assessed", [])
    temperature = any(k in assessed for k in ("temperature", "historical temperature"))
    soil = any(k in assessed for k in ("soil", "measured soil pH", "reported drainage"))
    return [
        ("Temperature", "Historical record checked" if temperature else "Not assessed"),
        ("Soil", "Reported conditions checked" if soil else "Not assessed"),
        ("Water", card["water"]),
    ]


def finding_list(rows):
    items = []
    for k, v in rows:
        v_str = str(v)
        dot_cls = (
            "as-f-dot-wait"
            if ("not assessed" in v_str.lower() or "unknown" in v_str.lower() or "check" in v_str.lower())
            else "as-f-dot-ok"
        )
        items.append(
            f'<div><dt><i class="as-f-dot {dot_cls}" aria-hidden="true"></i>{escape(k)}</dt>'
            f"<dd>{escape(v_str)}</dd></div>"
        )
    return '<dl class="as-findings">' + "".join(items) + "</dl>"


def missing_text(card, limit=None):
    values = [UNKNOWN.get(k, k) for k in card.get("unknown", [])]
    shown = values if limit is None else values[:limit]
    suffix = "; more in details" if limit is not None and len(values) > limit else ""
    return ", ".join(shown) + suffix


def progress(stage):
    body = "".join(
        f"<li"
        + (' aria-current="step"' if n == stage else "")
        + f"><b>{n}</b>{label}</li>"
        for n, label in enumerate(("Location", "Field", "Season"), 1)
    )
    st.html('<ol class="as-steps" aria-label="Farm setup progress">' + body + "</ol>")


def downloads(dataset, farm, cards, weights, context):
    from .finder_report import make_record, readable

    record = make_record(dataset, farm, cards, weights, context)
    st.download_button(
        "Download report",
        readable(record),
        "agroshift-report.html",
        "text/html",
        on_click="ignore",
        key="farmer_download",
        type="primary",
    )
    with st.expander("More download formats", key="farmer_formats"):
        st.download_button(
            "Assessment data (JSON)",
            json.dumps(record, indent=2),
            "agroshift-crops.json",
            "application/json",
            on_click="ignore",
        )
        st.download_button(
            "Weather history (CSV)",
            dataset.frame.to_csv(),
            "agroshift-weather.csv",
            "text/csv",
            on_click="ignore",
        )
    caption("Includes the field inputs, scientific sources and remaining limitations.")


def empty_state(title, message):
    st.html(
        f'<section class="as-empty"><h2>{escape(title)}</h2><p>{escape(message)}</p></section>'
    )


def header():
    from .finder_ui import S, go
    from .finder_style import BRAND

    with st.container(
        horizontal=True,
        vertical_alignment="center",
        horizontal_alignment="distribute",
        key="app_header",
    ):
        st.html(BRAND, width="content")
        with st.container(horizontal=True, width="content", key="navigation"):
            for label, target in (
                ("Dashboard", "home"),
                ("My Farm", "my_farm"),
                ("Recommendations", "results"),
                ("Explore", "research"),
            ):
                active = (
                    S.page == target
                    or (
                        target == "results"
                        and S.page in ("compare", "details", "downloads")
                    )
                    or (
                        target == "my_farm"
                        and S.page in ("location", "conditions", "season")
                    )
                )
                if st.button(
                    label, type="primary" if active else "tertiary", key="nav_" + target
                ):
                    go(target)
        if S.farm:
            with st.container(width="content", key="farm_context"):
                if st.button(
                    S.farm_name or "Selected field",
                    icon=":material/location_on:",
                    key="selected_field",
                    help="Manage the selected farm",
                ):
                    go("my_farm")


def satellite_map(lat: float, lon: float, zoom: int = 12, label: str | None = None, boundary: dict | None = None):
    """Build a Folium map with EOX Sentinel-2 cloudless (CC BY 4.0) + OpenStreetMap switcher."""
    import folium

    m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None, control_scale=True)
    folium.TileLayer(
        tiles="https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg",
        attr='Sentinel-2 cloudless - <a href="https://s2maps.eu">s2maps.eu</a> by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016, CC BY 4.0)',
        name="Satellite (Sentinel-2 cloudless)",
        max_zoom=18,
    ).add_to(m)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Street & terrain map (OSM)",
    ).add_to(m)
    if boundary:
        folium.GeoJson(
            boundary,
            name="Field boundary",
            style_function=lambda _: {
                "color": "#F5EDDA",
                "weight": 3,
                "fillColor": "#3F8F55",
                "fillOpacity": 0.28,
            },
        ).add_to(m)
    folium.CircleMarker(
        [lat, lon],
        radius=8,
        color="#FFFFFF",
        weight=2.5,
        fill=True,
        fill_color="#1F6B3A",
        fill_opacity=1.0,
        tooltip=label or f"{lat:.4f}, {lon:.4f}",
    ).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    return m


def render_site_intelligence_banner(dataset, context: dict | None, point: tuple | None):
    """Automatically display the site's NASA climate & SoilGrids snapshot once a location is loaded."""
    if dataset is None or not point:
        return
    from .climate_insights import site_summary

    info = site_summary(dataset)
    soil = (context or {}).get("soil", {})
    soil_val = soil.get("value")
    gp = info["growing_period"]
    if gp["run"]:
        s_m, e_m, n_m = gp["run"]
        gp_text = f"{calendar.month_abbr[s_m]}–{calendar.month_abbr[e_m]} ({n_m} mo)"
    else:
        gp_text = f"{info['supported_months']} of 12 mo"
    rain_str = f"{info['annual_rain_mm']:,.0f} mm" if info["annual_rain_mm"] is not None else "—"
    et0_str = f"ET₀ {info['annual_et0_mm']:,.0f} mm/yr" if info["annual_et0_mm"] is not None else "Hargreaves ET₀"
    temp_str = f"{info['mean_temp_c']:.1f} °C" if info["mean_temp_c"] is not None else "—"
    if info["coolest_tmin_c"] is not None and info["hottest_tmax_c"] is not None:
        temp_sub = f"Range {info['coolest_tmin_c']:.0f}–{info['hottest_tmax_c']:.0f} °C"
    else:
        temp_sub = "25-yr daily mean"
    ph_str = f"pH {soil_val:.1f}" if isinstance(soil_val, (int, float)) else "Not mapped"
    ph_sub = "SoilGrids 0–5 cm model (not a field test)" if isinstance(soil_val, (int, float)) else "Use a field test if known"

    ic_rain = '<svg viewBox="0 0 24 24" fill="none" stroke="#1F5F9E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/></svg>'
    ic_temp = '<svg viewBox="0 0 24 24" fill="none" stroke="#B4472A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/></svg>'
    ic_cal = '<svg viewBox="0 0 24 24" fill="none" stroke="#1F6B3A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
    ic_soil = '<svg viewBox="0 0 24 24" fill="none" stroke="#6B4F35" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h20"/><path d="M2 17h20"/><path d="M12 2v10"/><path d="M12 7c3 0 5-2 5-5-3 0-5 2-5 5z"/></svg>'
    st.html(
        '<section class="as-intel-panel" aria-label="Automated location intelligence">'
        '<div class="as-intel-header">'
        f'<span class="as-intel-title">◈ Automated Environmental Snapshot · {escape(str(point[3]))}</span>'
        f'<span class="as-intel-badge">NASA POWER {escape(info["years"])} · Verified</span>'
        "</div>"
        '<div class="as-kpi-grid">'
        f'<div class="as-kpi-tile as-kpi-rain"><div class="as-kpi-label">{ic_rain}Annual Rainfall</div>'
        f'<div class="as-kpi-value">{escape(rain_str)}</div><div class="as-kpi-sub">{escape(et0_str)}</div></div>'
        f'<div class="as-kpi-tile as-kpi-temp"><div class="as-kpi-label">{ic_temp}Mean Temperature</div>'
        f'<div class="as-kpi-value">{escape(temp_str)}</div><div class="as-kpi-sub">{escape(temp_sub)}</div></div>'
        f'<div class="as-kpi-tile as-kpi-season"><div class="as-kpi-label">{ic_cal}Rain-Supported Window</div>'
        f'<div class="as-kpi-value">{escape(gp_text)}</div><div class="as-kpi-sub">Months where rain ≥ ½ ET₀</div></div>'
        f'<div class="as-kpi-tile as-kpi-soil"><div class="as-kpi-label">{ic_soil}Modelled Topsoil pH</div>'
        f'<div class="as-kpi-value">{escape(ph_str)}</div><div class="as-kpi-sub">{escape(ph_sub)}</div></div>'
        "</div>"
        "</section>"
    )


def render_calendar_strip(dataset, selected_window=None):
    """Render a 12-month visual agro-climatic strip showing monthly rain, temperature, and selected months."""
    if dataset is None:
        return
    from .climate_insights import site_summary, window_months

    info = site_summary(dataset)
    clim = info["climatology"]
    gp = info["growing_period"]
    supported = set(gp["supported"])
    selected = set(window_months(selected_window))
    max_rain = float(clim["rain_mm"].max()) if clim["rain_mm"].notna().any() and clim["rain_mm"].max() > 0 else 1.0

    cells = []
    for m in range(1, 13):
        row = clim.loc[m]
        r_val = row["rain_mm"]
        t_val = row["t_mean"]
        pct = min(100, max(4, round((float(r_val) / max_rain) * 100))) if r_val == r_val else 0
        classes = ["as-cal-cell"]
        if m in supported:
            classes.append("as-cal-supported")
        if m in selected:
            classes.append("as-cal-selected")
        r_txt = f"{r_val:.0f}mm" if r_val == r_val else "—"
        t_txt = f"{t_val:.0f}°C" if t_val == t_val else "—"
        cells.append(
            f'<div class="{" ".join(classes)}">'
            f'<span class="as-cal-m">{calendar.month_abbr[m]}</span>'
            f'<div class="as-cal-bar-track"><div class="as-cal-bar-fill" style="width:{pct}%"></div></div>'
            f'<span class="as-cal-rain">{r_txt}</span>'
            f'<span class="as-cal-temp">{t_txt}</span>'
            "</div>"
        )
    st.html(
        '<div class="as-cal-wrap">'
        '<div class="as-cal-head">'
        "<strong>12-Month Agro-Climatic Calendar (NASA 25-Year Monthly Means)</strong>"
        '<div class="as-cal-legend">'
        '<span><i class="as-cal-dot" style="background:#E6F4EA;border:1px solid #95CFA6"></i>Rain-supported (Rain ≥ ½ ET₀)</span>'
        '<span><i class="as-cal-dot" style="background:#F5EDDA;border:1px solid #C8962E"></i>Your selected growing window</span>'
        "</div>"
        "</div>"
        f'<div class="as-cal-strip">{"".join(cells)}</div>'
        f'<p class="as-caption" style="margin-top:8px">{escape(gp["note"])} {escape(gp["method"])}</p>'
        "</div>"
    )


def render_results_summary_strip(cards: list[dict], dataset, farm):
    """Render an at-a-glance KPI dashboard strip above the crop recommendation cards."""
    if not cards:
        return
    n_possible = sum(1 for c in cards if c["status"] == "possible")
    n_check = sum(1 for c in cards if c["status"] == "check")
    n_outside = sum(1 for c in cards if c["status"] in ("outside", "blocked"))
    n_unknown = sum(1 for c in cards if c["status"] == "unknown")
    win_label = farm.windows[0].label if farm and farm.windows else "Selected season"

    st.html(
        '<div class="as-intel-panel">'
        '<div class="as-kpi-grid">'
        f'<div class="as-kpi-tile" style="border-left:4px solid #17643A">'
        '<div class="as-kpi-label">● Worth Considering</div>'
        f'<div class="as-kpi-value" style="color:#17643A">{n_possible} crops</div>'
        '<div class="as-kpi-sub">Fit all checked references</div></div>'
        f'<div class="as-kpi-tile" style="border-left:4px solid #7A4D00">'
        '<div class="as-kpi-label">▲ Check Before Planting</div>'
        f'<div class="as-kpi-value" style="color:#7A4D00">{n_check} crops</div>'
        '<div class="as-kpi-sub">Partial evidence or caution</div></div>'
        f'<div class="as-kpi-tile" style="border-left:4px solid #8C3D0E">'
        '<div class="as-kpi-label">◆ Outside / Blocked</div>'
        f'<div class="as-kpi-value" style="color:#8C3D0E">{n_outside} crops</div>'
        '<div class="as-kpi-sub">Outside reference bounds</div></div>'
        f'<div class="as-kpi-tile" style="border-left:4px solid #1F5F9E">'
        '<div class="as-kpi-label">Growing Window</div>'
        f'<div class="as-kpi-value" style="font-size:16px">{escape(win_label)}</div>'
        f'<div class="as-kpi-sub">{len(cards)} total crops evaluated ({n_unknown} need more info)</div></div>'
        "</div></div>"
    )


def render_gaez_dual_card(lat: float, lon: float, mapped_crop: str):
    """Automatically look up both Rain-fed and Irrigated FAO GAEZ v5 classes and render the 8-class legend."""
    from .providers import gaez_point

    rows_html = []
    for sys_key, sys_label in (("rainfed", "Rain-fed (Low Input)"), ("irrigated", "Irrigated (Low Input)")):
        res = gaez_point(lat, lon, mapped_crop, sys_key)
        val = res.get("value") or "No data"
        steps = []
        for cls_name, bg, fg in GAEZ_SCALE:
            active = " as-gaez-active" if cls_name.lower() == str(val).lower() else ""
            steps.append(
                f'<div class="as-gaez-step{active}" style="background:{bg};color:{fg}">{escape(cls_name)}</div>'
            )
        rows_html.append(
            '<div class="as-gauge-card">'
            f'<div class="as-gauge-title"><span>FAO GAEZ v5 · {escape(sys_label)}</span>'
            f'<span style="color:var(--primary)">Class: {escape(str(val))}</span></div>'
            f'<div class="as-gaez-scale">{"".join(steps)}</div>'
            f'<p class="as-caption">{escape(res.get("detail", ""))}</p>'
            "</div>"
        )
    st.html("".join(rows_html))


def render_trait_visual_bars(crop_id: str, farm, context: dict | None = None):
    """Render visual range bars for preferred temperature and soil pH when published traits exist."""
    from .knowledge import global_traits

    traits = {t["trait"]: t for t in global_traits(crop_id)}
    blocks = []
    t_ref = traits.get("preferred_daily_mean_air_temperature")
    if t_ref:
        lo, hi = float(t_ref["low"]), float(t_ref["high"])
        left = max(0.0, min(100.0, (lo / 45.0) * 100.0))
        width = max(3.0, min(100.0 - left, ((hi - lo) / 45.0) * 100.0))
        blocks.append(
            '<div class="as-gauge-card">'
            '<div class="as-gauge-title"><span>Preferred Daily Mean Temperature</span>'
            f'<span>{lo:g}–{hi:g} °C (scale 0–45 °C)</span></div>'
            '<div class="as-range-track">'
            f'<div class="as-range-band" style="left:{left:.1f}%;width:{width:.1f}%"></div>'
            "</div>"
            f'<p class="as-caption">{escape(t_ref.get("source_title", ""))}</p>'
            "</div>"
        )
    ph_ref = traits.get("preferred_soil_ph")
    if ph_ref:
        lo, hi = float(ph_ref["low"]), float(ph_ref["high"])
        left = max(0.0, min(100.0, ((lo - 3.5) / 6.0) * 100.0))
        width = max(3.0, min(100.0 - left, ((hi - lo) / 6.0) * 100.0))
        marker_html = ""
        marker_note = "No field soil pH entered."
        if farm and farm.ph is not None:
            m_pos = max(0.0, min(98.0, ((float(farm.ph) - 3.5) / 6.0) * 100.0))
            marker_html = f'<div class="as-range-marker" style="left:{m_pos:.1f}%" title="Measured pH {farm.ph:g}"></div>'
            marker_note = f"Marker shows your measured field pH ({farm.ph:g})."
        elif context and isinstance(context.get("soil", {}).get("value"), (int, float)):
            est = float(context["soil"]["value"])
            m_pos = max(0.0, min(98.0, ((est - 3.5) / 6.0) * 100.0))
            marker_html = f'<div class="as-range-marker" style="left:{m_pos:.1f}%;background:#6B4F35" title="Modelled pH {est:.1f}"></div>'
            marker_note = f"Marker shows SoilGrids modelled topsoil pH ({est:.1f} — not a field measurement)."
        blocks.append(
            '<div class="as-gauge-card">'
            '<div class="as-gauge-title"><span>Preferred Soil pH Range</span>'
            f'<span>pH {lo:g}–{hi:g} (scale 3.5–9.5)</span></div>'
            '<div class="as-range-track">'
            f'<div class="as-range-band" style="left:{left:.1f}%;width:{width:.1f}%"></div>'
            f"{marker_html}"
            "</div>"
            f'<p class="as-caption">{escape(marker_note)} · {escape(ph_ref.get("source_title", ""))}</p>'
            "</div>"
        )
    if blocks:
        st.html("".join(blocks))


def build_climograph_figure(dataset, measure: str = "Combined climograph (Rain, ET₀ & Temp)"):
    """Build a single interactive Plotly figure combining monthly rain, Hargreaves ET₀, temperature or solar."""
    import plotly.graph_objects as go
    from .climate import aggregate
    from .climate_insights import site_summary

    info = site_summary(dataset)
    clim = info["climatology"]
    gp = info["growing_period"]
    months = list(calendar.month_abbr)[1:]

    fig = go.Figure()
    if measure in ("Combined climograph (Rain, ET₀ & Temp)", "Rainfall"):
        fig.add_trace(
            go.Bar(
                x=months,
                y=clim["rain_mm"],
                name="Monthly rainfall (mm)",
                marker_color="#1F5F9E",
                opacity=0.88,
                yaxis="y1",
            )
        )
        if clim["et0_mm"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=months,
                    y=clim["et0_mm"],
                    name="Reference ET₀ (mm)",
                    mode="lines+markers",
                    line=dict(color="#6B4F35", width=2.5, dash="dot"),
                    yaxis="y1",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=months,
                    y=0.5 * clim["et0_mm"],
                    name="FAO LGP threshold (½ ET₀)",
                    mode="lines",
                    line=dict(color="#3F8F55", width=1.8, dash="dash"),
                    yaxis="y1",
                )
            )
    if measure in ("Combined climograph (Rain, ET₀ & Temp)", "Temperature"):
        yaxis_t = "y2" if measure.startswith("Combined") else "y1"
        if clim["t_max"].notna().any() and clim["t_min"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=months + months[::-1],
                    y=list(clim["t_max"]) + list(clim["t_min"][::-1]),
                    fill="toself",
                    fillcolor="rgba(180,71,42,0.14)",
                    line=dict(color="rgba(180,71,42,0)"),
                    name="Mean daily min–max band (°C)",
                    yaxis=yaxis_t,
                    hoverinfo="skip",
                )
            )
        fig.add_trace(
            go.Scatter(
                x=months,
                y=clim["t_mean"],
                name="Mean temperature (°C)",
                mode="lines+markers",
                line=dict(color="#B4472A", width=3),
                marker=dict(size=7, color="#B4472A"),
                yaxis=yaxis_t,
            )
        )
    if measure == "Solar energy":
        monthly = aggregate(dataset.frame)
        solar = monthly["solar_mj_m2_day"].groupby(monthly.index.month).mean().reindex(range(1, 13))
        fig.add_trace(
            go.Bar(
                x=months,
                y=solar,
                name="Solar radiation (MJ/m²/day)",
                marker_color="#C8962E",
                yaxis="y1",
            )
        )

    for m in gp.get("supported", []):
        idx = m - 1
        fig.add_vrect(
            x0=idx - 0.45,
            x1=idx + 0.45,
            fillcolor="rgba(63,143,85,0.10)",
            line_width=0,
            layer="below",
        )

    layout_kwargs = dict(
        margin=dict(l=8, r=8, t=28, b=8),
        height=350,
        font=dict(family="Inter, sans-serif", color="#1B2A21", size=13),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F9F8F3",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        barmode="overlay",
    )
    if measure.startswith("Combined"):
        layout_kwargs["yaxis"] = dict(title="Water depth (mm/month)", gridcolor="#E5E8E3")
        layout_kwargs["yaxis2"] = dict(
            title="Temperature (°C)",
            overlaying="y",
            side="right",
            showgrid=False,
        )
    elif measure == "Rainfall":
        layout_kwargs["yaxis"] = dict(title="Monthly rain / ET₀ (mm)", gridcolor="#E5E8E3")
    elif measure == "Temperature":
        layout_kwargs["yaxis"] = dict(title="Monthly mean (°C)", gridcolor="#E5E8E3")
    else:
        layout_kwargs["yaxis"] = dict(title="Monthly mean (MJ/m²/day)", gridcolor="#E5E8E3")
    fig.update_layout(**layout_kwargs)
    return fig


def render_weather_extremes_strip(dataset, window):
    """Render a 4-tile seasonal weather extremes and decadal climate shift strip."""
    if dataset is None or window is None:
        return
    from .climate_insights import seasonal_weather_risk_summary

    risk = seasonal_weather_risk_summary(dataset, window)
    if not risk:
        return
    n = risk["seasons_evaluated"]
    frost_pct = round(100 * risk["frost_seasons"] / n)
    heat_pct = round(100 * risk["heat_seasons"] / n)
    heavy_pct = round(100 * risk["heavy_rain_seasons"] / n)
    dry14_pct = round(100 * risk["dry_spell_14d_seasons"] / n)
    frost_val = f"{risk['frost_seasons']} of {n} seasons ({frost_pct}%)"
    frost_sub = "No frost days (<0 °C) in record" if risk["frost_seasons"] == 0 else "Chilling/frost risk during window"
    heat_val = f"{risk['heat_seasons']} of {n} seasons ({heat_pct}%)"
    heat_sub = (
        f"Days >35 °C · Heavy rain (≥25 mm) in {heavy_pct}% of seasons"
        if risk["heat_seasons"] > 0
        else f"No >35 °C days · Heavy rain in {heavy_pct}% of seasons"
    )
    dry_val = f"{risk['median_dry_spell_days']:.0f} days median (max {risk['max_dry_spell_days']} d)"
    dry_sub = f"≥14-day dry spell in {dry14_pct}% of seasons"
    if risk["warming_delta_c"] is not None:
        shift_val = f"{risk['warming_delta_c']:+.2f} °C recent shift"
        dry_d = risk["dry_spell_delta_days"]
        shift_sub = (
            f"2013–2025 vs 2001–2012 · Dry spell {dry_d:+.1f} d"
            if dry_d is not None
            else "2013–2025 vs 2001–2012 seasonal mean"
        )
    else:
        gdd_str = f"{risk['median_gdd10']:,.0f} °C·d" if risk["median_gdd10"] is not None else "—"
        shift_val = f"GDD₁₀ {gdd_str}"
        shift_sub = "Median seasonal thermal time (base 10 °C)"

    st.html(
        '<section class="as-intel-panel" aria-label="Seasonal weather extremes and climate trend">'
        '<div class="as-intel-header">'
        f'<span class="as-intel-title">Seasonal Weather Stress & Decadal Shift · {escape(window.label)}</span>'
        f'<span class="as-intel-badge">{n} complete historical seasons analysed</span>'
        "</div>"
        '<div class="as-kpi-grid">'
        f'<div class="as-kpi-tile"><div class="as-kpi-label">Frost Exposure (&lt;0 °C)</div>'
        f'<div class="as-kpi-value">{escape(frost_val)}</div><div class="as-kpi-sub">{escape(frost_sub)}</div></div>'
        f'<div class="as-kpi-tile"><div class="as-kpi-label">Heat Stress (&gt;35 °C)</div>'
        f'<div class="as-kpi-value">{escape(heat_val)}</div><div class="as-kpi-sub">{escape(heat_sub)}</div></div>'
        f'<div class="as-kpi-tile"><div class="as-kpi-label">Longest Dry Spell</div>'
        f'<div class="as-kpi-value">{escape(dry_val)}</div><div class="as-kpi-sub">{escape(dry_sub)}</div></div>'
        f'<div class="as-kpi-tile"><div class="as-kpi-label">Decadal Climate Trend</div>'
        f'<div class="as-kpi-value">{escape(shift_val)}</div><div class="as-kpi-sub">{escape(shift_sub)}</div></div>'
        "</div>"
        "</section>"
    )


def render_sowing_heatmap_matrix(dataset, cards: list[dict]):
    """Render a 12-month × multi-crop sowing window compatibility matrix."""
    if dataset is None or not cards:
        return
    from .climate_insights import crop_12month_sowing_matrix

    matrix = crop_12month_sowing_matrix(dataset, cards, max_crops=8)
    if not matrix or not matrix.get("rows"):
        return
    rows = matrix["rows"]
    cell_meta = {
        "optimal": ("●", "as-m-opt", "Temp & rain fit"),
        "needs_water": ("▲", "as-m-irr", "Temp fits; needs irrigation"),
        "marginal": ("◆", "as-m-mar", "Near temperature margin"),
        "outside": ("✕", "as-m-out", "Outside temperature bounds"),
    }
    headers = "".join(f"<th>{calendar.month_abbr[m]}</th>" for m in range(1, 13))
    body_rows = []
    for r in rows:
        tds = []
        for cell in r["cells"]:
            sym, cls, tip = cell_meta.get(cell["state"], ("○", "as-m-mar", ""))
            tds.append(
                f'<td><span class="as-m-cell {cls}" title="{escape(cell["month_abbr"])}: {escape(tip)} ({cell["t_avg"]} °C, {cell["rain_mm"]:.0f} mm)">{sym}</span></td>'
            )
        best = ", ".join(r["best_sowing_months"][:4]) if r["best_sowing_months"] else "Needs irrigation / check"
        body_rows.append(
            f"<tr><td>{escape(r['name'])} <span style='font-weight:400;color:#47584C;font-size:11px'>({r['cycle_months']} mo)</span></td>"
            + "".join(tds)
            + f"<td style='text-align:left;font-size:12px;color:#1F6B3A;font-weight:600'>{escape(best)}</td></tr>"
        )
    st.html(
        '<div class="as-cal-wrap">'
        '<div class="as-cal-head">'
        "<strong>12-Month Sowing Window Explorer (If Planted in Each Month)</strong>"
        '<div class="as-cal-legend">'
        '<span><b style="color:#17643A">●</b> Temp &amp; rain fit</span>'
        '<span><b style="color:#7A4D00">▲</b> Temp fits (needs irrigation)</span>'
        '<span><b style="color:#8C3D0E">◆</b> Near temp margin</span>'
        '<span><b style="color:#667068">✕</b> Outside temp range</span>'
        "</div></div>"
        '<div style="overflow-x:auto">'
        '<table class="as-matrix-table">'
        f"<thead><tr><th>Crop (Duration)</th>{headers}<th style='text-align:left'>Best Rain-Supported Start</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table></div>"
        '<p class="as-caption" style="margin-top:8px">Evaluates published crop temperature bounds and FAO stage water demand against 25-year NASA monthly climatology for each starting month.</p>'
        "</div>"
    )


def render_stage_water_chart(crop_id: str, dataset, window):
    """Render 4-stage FAO-56 crop water demand (ETc = Kc × ET0) vs historical rainfall."""
    if dataset is None or window is None:
        return
    from .climate_insights import crop_stage_water_demand

    stages = crop_stage_water_demand(crop_id, dataset, window)
    if not stages:
        return
    max_mm = max(max(s["etc_mm"], s["rain_mm"]) for s in stages) or 1.0
    cards_html = []
    for s in stages:
        etc_pct = min(100, max(5, round((s["etc_mm"] / max_mm) * 100)))
        rain_pct = min(100, max(5, round((s["rain_mm"] / max_mm) * 100)))
        deficit = s["deficit_mm"]
        cov_pct = min(100, round(100 * s["rain_mm"] / max(s["etc_mm"], 1.0)))
        peak_badge = (
            '<span style="background:#F5EDDA;color:#7A4D00;padding:1px 6px;border-radius:99px;font-size:10.5px;font-weight:700">Peak sensitivity</span>'
            if s["stage_key"] == "mid_season"
            else f'<span>Kc {s["kc"]:.2f}</span>'
        )
        status_note = (
            f"Historical rain covers ~{cov_pct}%"
            if deficit <= 10
            else f"Gap ~{deficit:.0f} mm (covers {cov_pct}%)"
        )
        cards_html.append(
            '<div class="as-stage-card">'
            f'<div class="as-stage-name">{escape(s["label"])}</div>'
            f'<div class="as-stage-meta"><span>~{s["days"]} days</span>{peak_badge}</div>'
            f'<div style="font-size:11.5px;color:#47584C;margin-top:4px">Crop demand (ETc): <b style="color:#8C3D0E">{s["etc_mm"]:.0f} mm</b></div>'
            f'<div class="as-stage-bar"><div style="width:{etc_pct}%;height:100%;background:#C8962E;border-radius:99px"></div></div>'
            f'<div style="font-size:11.5px;color:#47584C;margin-top:4px">Historical rain: <b style="color:#1F5F9E">{s["rain_mm"]:.0f} mm</b></div>'
            f'<div class="as-stage-bar"><div style="width:{rain_pct}%;height:100%;background:#1F5F9E;border-radius:99px"></div></div>'
            f'<div style="font-size:11px;color:#47584C;margin-top:4px">{escape(status_note)}</div>'
            "</div>"
        )
    total_etc = sum(s["etc_mm"] for s in stages)
    total_rain = sum(s["rain_mm"] for s in stages)
    st.html(
        '<div class="as-gauge-card">'
        '<div class="as-gauge-title">'
        "<span>FAO-56 Growth-Stage Water Demand (ETc = Kc × ET₀) vs. Historical Rain</span>"
        f"<span>Total ETc ~{total_etc:.0f} mm · Rain ~{total_rain:.0f} mm</span>"
        "</div>"
        f'<div class="as-stage-grid">{"".join(cards_html)}</div>'
        '<p class="as-caption" style="margin-top:8px">Stage coefficients (Kc) from FAO Irrigation and Drainage Paper 56 (Allen et al., 1998). Flowering &amp; yield formation is the most drought-sensitive period.</p>'
        "</div>"
    )


def render_evidence_layers_card(crop_card: dict, farm, dataset, context: dict | None = None):
    """Render the 6-Layer Non-Compensatory Scientific Evidence Scorecard (Layers A–F)."""
    if not crop_card or not farm:
        return
    from .evidence_combination import build_evidence_layers
    from .extremes import summarize_historical_extremes
    from .knowledge import crop_by_id
    from .water_balance import seasonal_water_balance_summary

    c_ident = crop_by_id(crop_card["id"])
    p_ident = crop_by_id(farm.current) if farm.current not in (None, "unknown") else None
    soil_rec = (context or {}).get("soil")
    wb_summary = None
    ext_summary = None
    if dataset is not None and not dataset.frame.empty and farm.windows:
        wb_summary = seasonal_water_balance_summary(
            dataset.frame,
            farm.windows[0],
            latitude=farm.latitude,
            is_paddy=(crop_card["id"] == "rice"),
        )
        ext_summary = summarize_historical_extremes(dataset.frame, farm.windows[0])
    layers = build_evidence_layers(
        crop_card,
        farm,
        crop_identity=c_ident,
        previous_crop_identity=p_ident,
        water_balance=wb_summary,
        extremes=ext_summary,
        modelled_soil=soil_rec,
    )
    la = layers["layer_a_eligibility"]
    lb = layers["layer_b_hard_constraints"]
    lc = layers["layer_c_environmental"]
    ld = layers["layer_d_correlated_models"]
    le = layers["layer_e_farmer_context"]
    lf = layers["layer_f_classification"]

    cats = la["data_categories"]
    meas_str = ", ".join(cats["farmer_measurements"]) or "None entered"
    est_str = ", ".join(cats["farmer_estimates"]) or "None entered"
    unk_str = ", ".join(cats["unknown_information"]) or "None"
    hard_str = "; ".join(lb["hard_constraints"]) if lb["hard_constraints"] else "No hard biological/physical blockers triggered."
    soil_note = lc["soil_reconciliation"]["precedence_note"]
    if lc["soil_reconciliation"]["disagreement"].get("summary"):
        soil_note = lc["soil_reconciliation"]["disagreement"]["summary"]
    wb_note = ""
    if wb_summary and wb_summary.get("status") == "verified":
        wb_note = (
            f" · FAO-56 median ETc {wb_summary['etc_median_mm']:.0f} mm, "
            f"effective rain {wb_summary['effective_rain_median_mm']:.0f} mm "
            f"(stress days median {wb_summary['water_stress_days_median']:.0f} d)"
        )
    gaez_info = ld["gaez_v5"]
    gaez_str = (
        f"FAO GAEZ v5 ({gaez_info['water_regime']}): {gaez_info['suitability_class']} · {gaez_info['alignment_with_screening']}"
        if gaez_info.get("suitability_class")
        else "No mapped GAEZ v5 raster class for this crop."
    )
    fam_str = f"Botanical family: {le.get('crop_family') or 'Recorded in catalogue'}"
    if le.get("same_family_succession_warning"):
        fam_str += f" · Caution: {le['same_family_succession_warning']}"

    items = [
        ("Layer A · Scope & Data Provenance", f"Support: {la['support_scope']} · Measured: {meas_str} · Farmer estimates: {est_str}"),
        ("Layer B · Hard Agronomic Constraints", hard_str),
        ("Layer C · Environmental & Soil Reconciliation", f"Assessed: {', '.join(lc['assessed_factors']) or 'None'} · {soil_note}{wb_note}"),
        ("Layer D · Correlated Model Cross-Check", f"{gaez_str} (Never double-counted with NASA POWER)"),
        ("Layer E · Field Context & Crop Succession", f"{fam_str} · Still unknown: {unk_str}"),
        ("Layer F · Decision-Support Classification", f"{lf['classification_label']} — {lf['decision_support_disclaimer']}"),
    ]
    boxes = "".join(
        '<div class="as-layer-box">'
        f'<div class="as-layer-tag">{escape(title)}</div>'
        f'<div class="as-layer-body">{escape(body)}</div>'
        "</div>"
        for title, body in items
    )
    st.html(f'<div class="as-layer-grid">{boxes}</div>')


def render_voi_uncertainty_card(dataset, farm, cards: list[dict], weights: dict | None = None, context: dict | None = None):
    """Render the Value-of-Information (VoI) Uncertainty Narrowing Guide for missing field inputs."""
    if not cards or farm is None:
        return
    from .geography import pilot_scope
    from .soil_and_water import compute_general_screening_voi_guide, compute_uncertainty_narrowing_guide

    gen_voi = compute_general_screening_voi_guide(dataset, farm, cards, context)
    if not gen_voi.get("available") or not gen_voi.get("actions"):
        return

    regional = (
        dataset is not None
        and len(farm.windows) == 2
        and pilot_scope(farm.latitude, farm.longitude, farm.country, farm.pilot_confirmed)
    )
    rot_voi = (
        compute_uncertainty_narrowing_guide(dataset.frame, farm, weights or {"temperature": 25, "water": 25, "soil": 25, "diversification": 25})
        if regional
        else None
    )
    rot_by_param = {a["parameter"]: a for a in (rot_voi or {}).get("actions", [])}

    soil_prior = gen_voi["soil_prior"]
    boxes = []
    for act in gen_voi["actions"]:
        p_key = act["parameter"]
        r_act = rot_by_param.get(p_key)
        gain_badge = (
            f"Narrows rotation interval by ±{r_act['impact_pts']:.1f} pts · {act['crops_affected']} crops affected"
            if r_act
            else f"Resolves checks across {act['crops_affected']} of {gen_voi['total_crops']} crops"
        )
        boxes.append(
            '<div class="as-layer-item">'
            f"<h4>{escape(act['title'])} · <span style='color:var(--primary)'>{escape(gain_badge)}</span></h4>"
            f"<p>{escape(act['explanation'])}<br><small style='color:var(--muted)'>{escape(act['suggested_label'])}</small></p>"
            "</div>"
        )
    header_sub = (
        f"Rotation preference interval width: ±{rot_voi['current_width']:.1f} pts ({rot_voi['evidence_coverage_pct']:.0f}% weight assessed)"
        if rot_voi and rot_voi.get("available")
        else f"SoilGrids / Regional reference: pH {soil_prior['ph_median']:.1f} ({soil_prior['usda_texture']}, AWC ~{soil_prior['hydraulics']['awc_mm_per_m']:.0f} mm/m)"
    )
    st.html(
        '<div class="as-gauge-card">'
        '<div class="as-gauge-title">'
        "<span>Value-of-Information (VoI) Guide · Highest-Leverage Field Checks</span>"
        f"<span>{escape(header_sub)}</span>"
        "</div>"
        f'<div class="as-layer-grid">{"".join(boxes)}</div>'
        '<p class="as-caption" style="margin-top:8px">Ranks missing field measurements by how many crop compatibility checks or preference interval points they resolve. Use <b>Edit my field</b> to supply any known measurement or schedule estimate.</p>'
        "</div>"
    )


def render_comparison_trait_table(ids: list[str], cards: list[dict], dataset, farm):
    """Render a side-by-side agronomic reference & FAO GAEZ v5 comparison table for the selected crops."""
    if len(ids) < 2:
        return
    from .knowledge import crop_by_id, global_traits
    from .providers import GAEZ_CROP_ID_MAP, gaez_point

    by_id = {c["id"]: c for c in cards}
    chosen = [by_id[i] for i in ids if i in by_id]
    if len(chosen) < 2:
        return

    all_traits = {}
    for row in global_traits():
        if row.get("review_status") == "reviewed" and row.get("scope") == "global":
            all_traits.setdefault(row["crop_id"], {})[row["trait"]] = row

    headers = "".join(f"<th style='text-align:left;padding:8px 10px'>{escape(c['name'])}</th>" for c in chosen)
    metrics = [
        ("Screening Status", lambda c, _t, _id: STATUS.get(c["status"], c["status"])),
        ("Botanical Family", lambda _c, _t, ident: (ident or {}).get("family") or "—"),
        (
            "Preferred Daily Temp",
            lambda _c, t, _id: (
                f"{t['preferred_daily_mean_air_temperature']['low']:g}–{t['preferred_daily_mean_air_temperature']['high']:g} °C"
                if "preferred_daily_mean_air_temperature" in t
                else "Regional / not globally fixed"
            ),
        ),
        (
            "Preferred Soil pH",
            lambda _c, t, _id: (
                f"pH {t['preferred_soil_ph']['low']:g}–{t['preferred_soil_ph']['high']:g}"
                if "preferred_soil_ph" in t
                else "Not globally fixed"
            ),
        ),
        (
            "Seasonal Crop Water (ETc)",
            lambda _c, t, _id: (
                f"{t['seasonal_crop_et']['low']:g}–{t['seasonal_crop_et']['high']:g} mm"
                if "seasonal_crop_et" in t
                else "System-dependent"
            ),
        ),
        (
            "Indicative Cycle Duration",
            lambda _c, t, _id: (
                f"{t['indicative_cycle_duration']['low']:g}–{t['indicative_cycle_duration']['high']:g} days"
                if "indicative_cycle_duration" in t
                else "Variety-dependent"
            ),
        ),
        (
            "FAO GAEZ v5 (Rain-fed)",
            lambda c, _t, _id: (
                gaez_point(farm.latitude, farm.longitude, GAEZ_CROP_ID_MAP[c["id"]], "rainfed").get("value") or "—"
                if farm and c["id"] in GAEZ_CROP_ID_MAP
                else "Not mapped"
            ),
        ),
        (
            "FAO GAEZ v5 (Irrigated)",
            lambda c, _t, _id: (
                gaez_point(farm.latitude, farm.longitude, GAEZ_CROP_ID_MAP[c["id"]], "irrigated").get("value") or "—"
                if farm and c["id"] in GAEZ_CROP_ID_MAP
                else "Not mapped"
            ),
        ),
    ]

    rows_html = []
    for label, fn in metrics:
        tds = []
        for c in chosen:
            t_map = all_traits.get(c["id"], {})
            ident = crop_by_id(c["id"])
            val = fn(c, t_map, ident)
            tds.append(f"<td style='padding:8px 10px;border-top:1px solid var(--line);font-size:13px'>{escape(str(val))}</td>")
        rows_html.append(
            f"<tr><td style='padding:8px 10px;border-top:1px solid var(--line);font-weight:650;color:var(--muted);font-size:12.5px'>{escape(label)}</td>"
            + "".join(tds)
            + "</tr>"
        )

    st.html(
        '<div class="as-cal-wrap">'
        '<div class="as-cal-head"><strong>Side-by-Side Agronomic Reference &amp; GAEZ v5 Matrix</strong></div>'
        '<div style="overflow-x:auto">'
        '<table class="as-matrix-table" style="border-spacing:0">'
        f"<thead><tr><th style='text-align:left;padding:8px 10px'>Reference Dimension</th>{headers}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        "</table></div>"
        "</div>"
    )


