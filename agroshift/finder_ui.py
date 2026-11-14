"""The farmer's path: a location, a field, a season, and a small set of options."""

import calendar
from dataclasses import replace
import html

import pycountry
import streamlit as st

from .assistant import DEMO_SCENARIOS, LOCATION_PRESETS
from .climate import Window
from .decision import CRITERIA, CROPS, Farm
from .finder_style import BRAND, HERO, HOME_SHOWCASE, STYLE
from .geography import pilot_scope, search_places
from .locations import (
    countries_at,
    country_map_view,
    country_regions,
    load_history,
    stations,
)
from .power import DataError

S = st.session_state
WATER = {
    "unknown": "Not sure",
    "rainfed": "Rain only",
    "supplemental": "Sometimes irrigated",
    "reliable": "Regularly irrigated",
}
DRAIN = {
    "unknown": "Not sure",
    "well_drained": "Water drains away",
    "waterlogged": "Water stays standing for long periods",
}
LEVELS = {
    "general": "General crop reference",
    "regional": "Regional crop reference",
    "catalogue": "Name only",
}
TITLES = {
    "home": "Crop Finder",
    "location": "Where is your farm?",
    "conditions": "Tell us about your field",
    "season": "When do you plan to grow?",
    "results": "Your crop options",
    "compare": "Compare crops",
    "details": "Crop details",
    "research": "Research",
}
STATUS = {
    "possible": "Worth considering",
    "check": "Check before planting",
    "outside": "Outside the reference range",
    "blocked": "Doesn’t fit these conditions",
    "unknown": "Not enough information",
}


def init():
    for k, v in dict(
        page="home",
        return_page="home",
        target="farm",
        draft={},
        farm=None,
        dataset=None,
        point=None,
        cards=[],
        weights=dict.fromkeys(CRITERIA, 25),
        section="Crop catalogue",
        detail_id=None,
        card_page=0,
        places=[],
        demo_active=False,
        session_farms={},
        session_history={},
        active_farm_id=None,
        active_revision=0,
        farm_name="",
        boundary=None,
        context={},
        setup_page=None,
        comparison_ids=[],
    ).items():
        S.setdefault(k, v)


def go(page):
    from .ui_state import capture

    if S.page in ("conditions", "season"):
        capture()
    if page in ("location", "conditions", "season"):
        S.setup_page = page
    S.page = page
    st.rerun()


def start(target):
    S.target = target
    if target == "farm":
        from .ui_state import clear_wizard

        clear_wizard()
        S.draft = {}
        S.demo_active = False
        S.point = None
        S.dataset = None
        S.farm = None
        S.cards = []
        S.active_farm_id = None
        S.active_revision = 0
        S.farm_name = ""
        S.boundary = None
        S.context = {}
        S.comparison_ids = []
    go("location")


def research(topic):
    if S.page != "research":
        S.return_page = S.page
    S.section = topic
    S.pop("research_choice", None)
    go("research")


def home():
    st.html(HERO)
    with st.container(horizontal=True, key="home_actions"):
        if st.button("Analyze my farm", type="primary", key="start", icon=":material/agriculture:"):
            start("farm")
        if st.button("Browse crops", key="browse", icon=":material/grass:"):
            research("Crop catalogue")
        if st.button("Try an example farm", type="secondary", icon=":material/explore:"):
            demo()
    if S.setup_page:
        if st.button("Continue farm setup", icon=":material/arrow_forward:"):
            go(S.setup_page)
    st.html(HOME_SHOWCASE)


def demo(preset="scenario_1_well_drained"):
    from .ui_state import clear_wizard

    clear_wizard()
    farm = replace(
        DEMO_SCENARIOS[preset]["farm"],
        input_origin="fictional demonstration profile",
        irrigation_basis="illustrative scenario",
    )
    S.dataset = load_history(farm.latitude, farm.longitude)
    S.point = ("LK", farm.latitude, farm.longitude, "Anuradhapura")
    from .farm_context import location_context

    S.context = location_context("LK", farm.latitude, farm.longitude, offline=True)
    S.active_farm_id = None
    S.active_revision = 0
    S.farm_name = ""
    S.boundary = None
    S.demo_active = True
    S.target = "farm"
    S.draft = dict(
        drainage=farm.drainage,
        irrigation=farm.irrigation,
        ph=farm.ph,
        area_ha=farm.area_ha,
        irrigation_mm=farm.irrigation_mm,
        irrigation_basis=farm.irrigation_basis,
        rain_fraction=farm.rain_fraction,
        current=farm.current,
        previous=farm.previous,
        baseline=farm.baseline,
        pilot_confirmed=True,
        windows=farm.windows,
        season_name=farm.season_name,
    )
    finish(farm)


def finish(farm):
    from .screening import find_options

    farm.validate()
    with st.spinner("Checking crops for your field…"):
        cards = find_options(farm, S.dataset, weights=S.weights)
    from .farm_records import utc_now

    S.assessed_at = utc_now()
    S.farm = farm
    S.cards = cards
    S.card_page = 0
    S.pop("which_crop", None)
    S.pop("compare_ids", None)
    S.comparison_ids = []
    S.setup_page = None
    go("results")


def heading(stage):
    from .ui_components import progress

    progress(stage)
    st.title(TITLES[S.page], anchor=False)


def cc_name(code):
    obj = pycountry.countries.get(alpha_2=code)
    return obj.name if obj else code


def station_name(k):
    names = {
        "anuradhapura": "Anuradhapura",
        "nairobi_kenya": "Nairobi",
        "punjab_india": "Ludhiana",
        "ames_usa": "Ames",
        "iowa_usa": "Ames",
        "riverina_australia": "Wagga Wagga",
        "kandy": "Kandy",
        "mato_grosso_brazil": "Sinop",
        "cusco_peru": "Cusco",
        "addis_ethiopia": "Addis Ababa",
    }
    if k in names:
        return names[k]
    label = LOCATION_PRESETS.get(k, {}).get("label", "").partition(" · ")[2]
    return label.split(",")[0].split(" (")[0] or k.replace("_", " ").title()


def location():
    if S.target == "farm":
        heading(1)
    else:
        st.title("Explore climate data", anchor=False)
    codes = sorted([c.alpha_2 for c in pycountry.countries], key=cc_name)
    last = S.point
    cc = st.selectbox(
        "Country or territory",
        codes,
        index=codes.index(last[0]) if last else None,
        format_func=cc_name,
        placeholder="Choose a country",
        key="wf_country",
        persist_state="session",
    )
    point = None
    if cc:
        c_view = country_map_view(cc)
        regions = country_regions(cc)
        nearby = [k for k, v in stations().items() if v[0] == cc]
        season_desc = (
            "Yala (May–Aug) & Maha (Oct–Feb) Bimodal Monsoon"
            if cc == "LK"
            else (c_view.get("default_season") or "Local seasonal calendar")
        )
        st.html(
            f'<div class="ag-context-bar" style="margin-bottom:0.65rem">'
            f'<div><small>Selected country</small><strong>{html.escape(cc_name(cc))}</strong>'
            f'{(" · " + html.escape(c_view["continent"])) if c_view.get("continent") else ""}</div>'
            f'<div><small>Typical seasonal pattern</small><strong>{html.escape(season_desc)}</strong></div>'
            f'<div><small>Reference hubs</small><strong>{len(regions)} regional center{"s" if len(regions) != 1 else ""}</strong></div>'
            f"</div>"
        )
        methods = (
            ["Search by name"]
            + (["Saved locations"] if nearby else [])
            + ["Map", "Coordinates"]
        )
        method = st.selectbox(
            "Find your field", methods, key="wf_method_" + cc, persist_state="session"
        )
        if method == "Saved locations":
            key = st.selectbox(
                "Location",
                nearby,
                format_func=station_name,
                index=None,
                placeholder="Choose a nearby location",
                key="wf_station_" + cc,
                persist_state="session",
            )
            if key:
                point = (*stations()[key], station_name(key))
            elif len(regions) > 1:
                reg_pick = st.selectbox(
                    "Or choose an agricultural district / regional hub",
                    range(len(regions)),
                    index=None,
                    placeholder="Choose a regional agro-climatic zone",
                    format_func=lambda i: regions[i]["label"],
                    key="wf_saved_reg_" + cc,
                )
                if reg_pick is not None:
                    r_item = regions[reg_pick]
                    short_lbl = r_item["label"].split(" · ")[0].split(" (")[0]
                    point = (cc, r_item["lat"], r_item["lon"], short_lbl)
        elif method == "Coordinates":
            a, b = st.columns(2)
            lat = a.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=last[1] if last and last[0] == cc else None,
                format="%.5f",
                key="wf_lat",
                persist_state="session",
            )
            lon = b.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=last[2] if last and last[0] == cc else None,
                format="%.5f",
                key="wf_lon",
                persist_state="session",
            )
            if lat is not None and lon is not None:
                point = (cc, lat, lon, cc_name(cc))
        elif method == "Search by name":
            with st.form("town_" + cc):
                q = st.text_input(
                    "Town or village", key="wf_town_" + cc, persist_state="session"
                )
                submit = st.form_submit_button("Search", type="primary")
            if submit:
                S.places = []
                try:
                    S.places = [
                        (cc, p)
                        for p in search_places(q, cc)
                        if p.get("country_code", cc) == cc
                    ]
                except DataError as e:
                    st.error(str(e))
                if not S.places:
                    st.info("No places found. Try coordinates, Map view, or a nearby town.")
            hits = [p for c, p in S.places if c == cc]
            if hits:
                n = st.selectbox(
                    "Matching places",
                    range(len(hits)),
                    index=None,
                    key="wf_place_" + cc,
                    persist_state="session",
                    format_func=lambda i: ", ".join(
                        str(hits[i][k]) for k in ("name", "admin1") if hits[i].get(k)
                    ),
                )
                if n is not None:
                    point = (
                        cc,
                        hits[n]["latitude"],
                        hits[n]["longitude"],
                        hits[n]["name"],
                    )
            st.caption("Place names: Open-Meteo / GeoNames. Tip: Switch to 'Map' above to browse by region or tap your field on satellite imagery.")
        else:
            from folium.plugins import Draw, LocateControl
            from streamlit_folium import st_folium
            from .farm_records import polygon_area_hectares
            from .ui_components import satellite_map

            reg_idx = st.selectbox(
                "Region or agricultural zone (centers map on your area)",
                range(len(regions)),
                index=0,
                format_func=lambda i: regions[i]["label"],
                key="wf_map_region_" + cc,
            )
            chosen_reg = regions[reg_idx]
            reg_short = chosen_reg["label"].split(" · ")[0].split(" (")[0]
            if reg_idx == 0 and last and last[0] == cc:
                center = [last[1], last[2]]
                zoom_lvl = max(chosen_reg["zoom"], 8)
                active_label = last[3]
            else:
                center = [chosen_reg["lat"], chosen_reg["lon"]]
                zoom_lvl = chosen_reg["zoom"]
                active_label = reg_short

            m = satellite_map(
                center[0],
                center[1],
                zoom=zoom_lvl,
                label=active_label,
            )
            LocateControl(auto_start=False, strings={"title": "Use my GPS location"}).add_to(m)
            Draw(
                draw_options={
                    "polyline": False,
                    "rectangle": False,
                    "circle": False,
                    "marker": False,
                    "circlemarker": False,
                    "polygon": {"allowIntersection": False},
                },
                edit_options={"edit": False, "remove": True},
            ).add_to(m)
            hit = st_folium(
                m,
                height=360,
                use_container_width=True,
                returned_objects=["last_clicked", "all_drawings"],
                key=f"map_{cc}_{reg_idx}",
            )
            # Pre-select the active region/country pin so the marker shown on the map is immediately usable,
            # and override it whenever the user clicks a point on the map or outlines a field polygon.
            point = (
                cc,
                round(float(center[0]), 5),
                round(float(center[1]), 5),
                active_label,
            )
            drawn_poly = None
            drawn_ha = None
            if hit and hit.get("all_drawings"):
                cand_geom = hit["all_drawings"][-1].get("geometry")
                if isinstance(cand_geom, dict) and cand_geom.get("type") == "Polygon":
                    ring = (cand_geom.get("coordinates") or [[]])[0]
                    if len(ring) >= 4:
                        pts = ring[:-1]
                        c_lon = round(sum(float(p[0]) for p in pts) / len(pts), 5)
                        c_lat = round(sum(float(p[1]) for p in pts) / len(pts), 5)
                        point = (cc, c_lat, c_lon, active_label)
                        drawn_poly = cand_geom
                        drawn_ha = polygon_area_hectares(cand_geom)
            if hit and hit.get("last_clicked") and not drawn_poly:
                point = (
                    cc,
                    round(hit["last_clicked"]["lat"], 5),
                    round(hit["last_clicked"]["lng"], 5),
                    active_label,
                )
            if drawn_ha is not None:
                acres = drawn_ha * 2.47105
                perches = acres * 160.0
                sqm = drawn_ha * 10000.0
                st.caption(
                    f"Drawn field boundary detected: **{drawn_ha:.2f} ha** · **{acres:.2f} acres** · **{perches:.0f} perches** ({sqm:,.0f} m²). Clicking **Use this location** will prefill your field area."
                )
                S["_pending_drawn_ha"] = drawn_ha
                S["_pending_drawn_poly"] = drawn_poly
            st.caption("Choose a region above to center the map, then tap your exact field, use the GPS button, or draw your field polygon to auto-calculate farm area. Imagery: Sentinel-2 cloudless (EOX / Copernicus 2016, CC BY 4.0).")
    if point:
        from .ui_components import context_bar, satellite_map

        context_bar(
            [
                ("Selected location", point[3]),
                ("Coordinates", f"{point[1]:.4f}, {point[2]:.4f}"),
            ]
        )
        if method != "Map" and st.checkbox("Preview on a map", key="wf_preview"):
            from streamlit_folium import st_folium

            preview = satellite_map(point[1], point[2], zoom=12, label=point[3])
            st_folium(
                preview,
                height=250,
                use_container_width=True,
                returned_objects=[],
                key="location_preview",
            )

    with st.container(horizontal=True):
        submit = st.button("Use this location", type="primary", disabled=not point)
        back = st.button("Back", key="location_back")
    if back:
        go("home")
    if submit:
        if S.point != point:
            # A newly selected field must not inherit persistent widgets from another farm.
            location_keys = (
                "wf_country",
                "wf_method",
                "wf_station",
                "wf_place",
                "wf_lat",
                "wf_lon",
                "wf_town",
                "wf_preview",
            )
            for key in list(S):
                if key.startswith("wf_") and not key.startswith(location_keys):
                    del S[key]
            S.dataset = None
            S.cards = []
            S.farm = None
            S.draft = {}
            S.demo_active = False
            S.context = {}
            S.boundary = None
            S.active_farm_id = None
            S.active_revision = 0
            S.farm_name = ""
        pending_ha = S.pop("_pending_drawn_ha", None)
        pending_poly = S.pop("_pending_drawn_poly", None)
        if pending_ha is not None:
            S.draft["area_ha"] = pending_ha
            S["wf_area_ha"] = pending_ha
            S.boundary = pending_poly
        S.point = point
        located = countries_at(point[1], point[2])
        if cc not in located and method not in ("Saved locations", "Search by name"):
            st.warning(
                "This point does not match the selected country on the land map. Choose a nearby named place for small islands or border fields."
            )
            return
        try:
            if S.dataset is None:
                with st.spinner("Loading weather history for this location…"):
                    S.dataset = load_history(point[1], point[2])
        except DataError as e:
            S.dataset = None
            S.cards = []
            S.farm = None
            st.error(
                "Environmental records are unavailable for this location right now. Retry Use this location, or choose a saved location."
            )
            with st.expander("Connection details"):
                st.text(str(e))
            return
        from .farm_context import location_context

        with st.spinner("Checking soil and local references…"):
            S.context = location_context(*point[:3])
        if S.target == "climate":
            research("Climate history")
        go("conditions")


def choice(label, options, d, key):
    from .ui_state import capture

    return st.selectbox(
        label,
        list(options),
        index=list(options).index(d.get(key, "unknown")),
        format_func=options.get,
        key="wf_" + key,
        persist_state="session",
        on_change=capture,
    )


def conditions():
    from .ui_state import capture
    from .ui_components import caption, render_site_intelligence_banner

    heading(2)
    render_site_intelligence_banner(S.dataset, S.context, S.point)
    d = S.draft
    st.text_input(
        "Farm name (optional)",
        value=S.farm_name,
        max_chars=80,
        key="wf_farm_name",
        persist_state="session",
        on_change=capture,
    )
    water = choice("Where does your water come from?", WATER, d, "irrigation")
    drain = choice("Does water remain after heavy rain?", DRAIN, d, "drainage")
    confirmed = False
    if pilot_scope(S.point[1], S.point[2], S.point[0], True):
        from .soil_and_water import detect_sri_lanka_aer

        aer_info = detect_sri_lanka_aer(S.point[1], S.point[2])
        if aer_info.get("in_sri_lanka"):
            caption(
                f"Detected agro-ecological zone: {aer_info['aer_code']} · Predominant soils: {aer_info['great_soil_group']} ({aer_info['source']})."
            )
        confirmed = st.checkbox(
            "My field is in Sri Lanka’s lowland dry or intermediate zone",
            value=d.get("pilot_confirmed", False),
            key="wf_pilot_confirmed",
            persist_state="session",
            on_change=capture,
        )
    with st.expander("Field measurements (optional)", key="measurements_panel"):
        caption("Leave any measurement blank if you do not know it.")
        ctx = S.context.get("soil", {})
        from .soil_and_water import (
            PH_STRIP_PRESETS,
            RIBBON_TEST_PRESETS,
            fetch_soil_profile,
        )
        from .soil import reconcile_soil_evidence

        soil_prior = fetch_soil_profile(S.point[1], S.point[2], allow_network=False)
        if ctx.get("value") is not None:
            caption(
                f"Estimated soil pH: {ctx['value']:.1f} (SoilGrids, top 5 cm · {soil_prior['usda_texture']}, AWC ~{soil_prior['hydraulics']['awc_mm_per_m']:.0f} mm/m). Your field test takes precedence."
            )
        else:
            caption(
                f"Regional soil reference: pH ~{soil_prior['ph_median']:.1f} ({soil_prior['usda_texture']}, AWC ~{soil_prior['hydraulics']['awc_mm_per_m']:.0f} mm/m). Your field test takes precedence."
            )
        a, b = st.columns(2)
        ph = a.number_input(
            "Measured soil pH",
            0.0,
            14.0,
            value=d.get("ph"),
            step=0.1,
            key="wf_ph",
            persist_state="session",
            on_change=capture,
        )
        area = b.number_input(
            "Field area (hectares)",
            min_value=0.01,
            value=d.get("area_ha"),
            key="wf_area_ha",
            persist_state="session",
            on_change=capture,
        )
        if area is not None:
            caption(
                f"Converted field size: **{area:.2f} ha** = **{area * 2.47105:.2f} acres** · **{area * 395.368:.0f} perches** · **{area * 10000:,.0f} m²**"
            )
        if ph is not None and ctx.get("value") is not None:
            reconciled = reconcile_soil_evidence(ph, ctx)
            if reconciled["disagreement"].get("summary"):
                caption(reconciled["disagreement"]["summary"])
        plot_scales = {
            "unselected": ("Choose a common farm scale or enter Acres / Perches below", None),
            "p20": ("Home garden / 20 Perches (~0.05 ha / 0.125 acre)", 0.05),
            "p40": ("Quarter-Acre plot / 40 Perches (~0.10 ha / 0.25 acre)", 0.10),
            "p80": ("Half-Acre plot / 80 Perches (~0.20 ha / 0.50 acre)", 0.20),
            "ac1": ("1 Acre smallholder plot (~0.40 ha / 160 perches)", 0.40),
            "ac2": ("2 Acres family farm (~0.81 ha / 320 perches)", 0.81),
            "ha1": ("1 Hectare / 2.5 Acres (~1.00 ha / 395 perches)", 1.00),
            "ac5": ("5 Acres medium farm (~2.02 ha)", 2.02),
            "ac10": ("10 Acres commercial block (~4.05 ha)", 4.05),
        }
        st.markdown("**Know your land size in Acres or Perches? Convert to Hectares**")
        ac_col1, ac_col2, ac_col3 = st.columns([2, 1, 1])
        scale_key = ac_col1.selectbox(
            "Quick plot size preset",
            list(plot_scales),
            format_func=lambda k: plot_scales[k][0],
            key="helper_plot_scale",
        )
        acres_in = ac_col2.number_input(
            "Acres",
            min_value=0.0,
            max_value=5000.0,
            value=0.0,
            step=0.25,
            key="helper_acres_in",
        )
        perches_in = ac_col3.number_input(
            "Perches (160 = 1 ac)",
            min_value=0.0,
            max_value=16000.0,
            value=0.0,
            step=10.0,
            key="helper_perches_in",
        )
        calc_ha_from_units = round(float(acres_in) * 0.404686 + float(perches_in) * 0.00252929, 2)
        target_ha = (
            calc_ha_from_units
            if calc_ha_from_units > 0
            else plot_scales[scale_key][1]
        )

        def _apply_area_unit_cb():
            sk = S.get("helper_plot_scale", "unselected")
            ac_v = float(S.get("helper_acres_in", 0.0) or 0.0)
            pe_v = float(S.get("helper_perches_in", 0.0) or 0.0)
            from_u = round(ac_v * 0.404686 + pe_v * 0.00252929, 2)
            ha_val = from_u if from_u > 0 else plot_scales.get(sk, (None, None))[1]
            if ha_val is not None and ha_val >= 0.01:
                S["wf_area_ha"] = ha_val
                S.setdefault("draft", {})["area_ha"] = ha_val

        st.button(
            f"Apply field area ({target_ha:.2f} ha)" if target_ha else "Apply converted field area",
            key="apply_area_converter",
            icon=":material/straighten:",
            disabled=(target_ha is None or target_ha < 0.01),
            on_click=_apply_area_unit_cb,
        )
        st.markdown("**Or estimate from a 2-minute field ribbon test & pH strip**")
        caption(
            "No laboratory report? Squeeze moist soil between thumb and forefinger (USDA-NRCS ribbon test) or match a colorimetric pH strip."
        )
        s_col1, s_col2 = st.columns(2)
        ribbon_key = s_col1.selectbox(
            "Hand texture check (ball & ribbon test)",
            list(RIBBON_TEST_PRESETS),
            format_func=lambda k: RIBBON_TEST_PRESETS[k]["label"],
            key="helper_ribbon_test",
        )
        ph_strip_key = s_col2.selectbox(
            "pH test strip / reference band",
            list(PH_STRIP_PRESETS),
            format_func=lambda k: PH_STRIP_PRESETS[k]["label"],
            key="helper_ph_strip",
        )
        rib_type = RIBBON_TEST_PRESETS[ribbon_key]["soil_type"]
        strip_raw = PH_STRIP_PRESETS[ph_strip_key]["ph_value"]
        resolved_strip_ph = (
            float(ctx["value"] if ctx.get("value") is not None else soil_prior["ph_median"])
            if strip_raw == "PRIOR"
            else strip_raw
        )

        def _apply_soil_field_check_cb():
            rk = S.get("helper_ribbon_test", "unselected")
            pk = S.get("helper_ph_strip", "unselected")
            rt = RIBBON_TEST_PRESETS.get(rk, {}).get("soil_type", "unknown")
            pv = PH_STRIP_PRESETS.get(pk, {}).get("ph_value")
            draft_state = S.setdefault("draft", {})
            if rt != "unknown":
                S["wf_soil_type"] = rt
                draft_state["soil_type"] = rt
            if pv is not None:
                val = (
                    float(ctx["value"] if ctx.get("value") is not None else soil_prior["ph_median"])
                    if pv == "PRIOR"
                    else float(pv)
                )
                S["wf_ph"] = round(val, 1)
                draft_state["ph"] = round(val, 1)

        st.button(
            "Apply field check to soil profile",
            key="apply_soil_field_check",
            icon=":material/science:",
            disabled=(rib_type == "unknown" and resolved_strip_ph is None),
            on_click=_apply_soil_field_check_cb,
        )
    with st.expander("Water amounts (optional)", key="water_panel"):
        caption(
            "Only add amounts you know. Irrigation availability alone does not establish how much water a crop receives."
        )
        mm = None
        basis = "user supplied"
        if water != "rainfed":
            mm = st.number_input(
                "Net irrigation per season (mm)",
                min_value=0.0,
                value=(
                    None if d.get("irrigation") == "rainfed" else d.get("irrigation_mm")
                ),
                key="wf_irrigation_mm",
                persist_state="session",
                on_change=capture,
            )
            if mm is not None:
                basis = st.selectbox(
                    "Irrigation amount is",
                    ["estimate", "measurement"],
                    index=int(d.get("irrigation_basis") == "measurement"),
                    key="wf_irrigation_basis",
                    persist_state="session",
                    on_change=capture,
                )
        fraction = st.number_input(
            "Share of rain usable by crops (0 to 1)",
            0.0,
            1.0,
            value=d.get("rain_fraction"),
            help="A locally informed assumption, not a measurement from NASA.",
            key="wf_rain_fraction",
            persist_state="session",
            on_change=capture,
        )
        from .soil_and_water import (
            IRRIGATION_DELIVERY_MODES,
            IRRIGATION_SCHEDULE_PRESETS,
            LANDFORM_PRESETS,
        )

        st.markdown("**Or estimate from field landform & irrigation schedule**")
        caption(
            "Not sure of the exact fraction or millimeter depth? Choose your field slope/bunds and water schedule (or number of irrigations) below to calculate an operational estimate."
        )
        w_col1, w_col2 = st.columns(2)
        landform_key = w_col1.selectbox(
            "Field landform & runoff retention",
            list(LANDFORM_PRESETS),
            format_func=lambda k: LANDFORM_PRESETS[k]["label"],
            key="helper_landform",
        )
        sched_options = (
            ["unselected", "rainfed_none"]
            if water == "rainfed"
            else list(IRRIGATION_SCHEDULE_PRESETS)
        )
        sched_key = w_col2.selectbox(
            "Typical irrigation schedule",
            sched_options,
            format_func=lambda k: IRRIGATION_SCHEDULE_PRESETS[k]["label"],
            key="helper_irrig_schedule",
        )
        turn_mm = None
        if water != "rainfed":
            t_col1, t_col2 = st.columns(2)
            deliv_key = t_col1.selectbox(
                "Or calculate by water delivery method",
                list(IRRIGATION_DELIVERY_MODES),
                format_func=lambda k: IRRIGATION_DELIVERY_MODES[k]["label"],
                key="helper_delivery_mode",
            )
            turn_count = t_col2.number_input(
                "Number of irrigations per season",
                min_value=0,
                max_value=30,
                value=0,
                step=1,
                key="helper_turn_count",
            )
            mm_per_t = IRRIGATION_DELIVERY_MODES[deliv_key]["mm_per_turn"]
            if mm_per_t is not None and turn_count > 0:
                turn_mm = round(float(mm_per_t) * int(turn_count), 1)
                caption(
                    f"Calculated seasonal irrigation: **{turn_count} turns × {mm_per_t:.0f} mm = {turn_mm:.0f} mm net**"
                )
        lf_val = LANDFORM_PRESETS[landform_key]["rain_fraction"]
        sc_val = turn_mm if turn_mm is not None else IRRIGATION_SCHEDULE_PRESETS[sched_key]["irrigation_mm"]

        def _apply_water_translator_cb():
            lk = S.get("helper_landform", "unselected")
            sk = S.get("helper_irrig_schedule", "unselected")
            dk = S.get("helper_delivery_mode", "unselected")
            tc = int(S.get("helper_turn_count", 0) or 0)
            lv = LANDFORM_PRESETS.get(lk, {}).get("rain_fraction")
            mpt = IRRIGATION_DELIVERY_MODES.get(dk, {}).get("mm_per_turn")
            sv = (
                round(float(mpt) * tc, 1)
                if mpt is not None and tc > 0
                else IRRIGATION_SCHEDULE_PRESETS.get(sk, {}).get("irrigation_mm")
            )
            draft_state = S.setdefault("draft", {})
            cur_water = S.get("wf_irrigation", draft_state.get("irrigation", "unknown"))
            if lv is not None:
                S["wf_rain_fraction"] = lv
                draft_state["rain_fraction"] = lv
            if sv is not None and cur_water != "rainfed":
                S["wf_irrigation_mm"] = sv
                S["wf_irrigation_basis"] = "estimate"
                draft_state["irrigation_mm"] = sv
                draft_state["irrigation_basis"] = "estimate"

        st.button(
            "Apply estimated water amounts",
            key="apply_water_translator",
            icon=":material/water_drop:",
            disabled=(lf_val is None and sc_val is None),
            on_click=_apply_water_translator_cb,
        )
    with st.expander(
        "Quick-fill from a plain-language note or soil report (optional)",
        key="nlp_intake_panel",
    ):
        from .soil_and_water import parse_natural_language_farm_description

        caption(
            "Describe your field in everyday words (English, සිංහල, or தமிழ்) or paste a soil-test summary. Review the detected values below before applying."
        )
        nlp_text = st.text_area(
            "Describe your field or paste a soil-test note",
            placeholder="Example: 2.5 acres bunded kumbura, grew wee (paddy) last season, tank water 3 turns, clay loam soil, pH 6.2",
            key="helper_nlp_note",
            height=80,
        )
        parsed_nlp = parse_natural_language_farm_description(nlp_text, soil_prior)
        if parsed_nlp["explanations"]:
            st.markdown("**Detected field details (confirm before applying):**")
            for exp_line in parsed_nlp["explanations"]:
                st.markdown(f"- {exp_line}")

        def _apply_nlp_intake_cb():
            parsed = parse_natural_language_farm_description(
                S.get("helper_nlp_note", ""), soil_prior
            )
            ext = parsed["extracted"]
            draft_state = S.setdefault("draft", {})
            for k_field in (
                "irrigation",
                "drainage",
                "ph",
                "area_ha",
                "rain_fraction",
                "irrigation_mm",
                "irrigation_basis",
                "current",
                "soil_type",
            ):
                if k_field in ext and ext[k_field] is not None:
                    draft_state[k_field] = ext[k_field]
                    S["wf_" + k_field] = ext[k_field]

        st.button(
            "Apply confirmed details to my field",
            key="apply_nlp_intake",
            icon=":material/check_circle:",
            disabled=(parsed_nlp["detected_count"] == 0),
            on_click=_apply_nlp_intake_cb,
        )
    S.draft.update(
        irrigation=water,
        drainage=drain,
        ph=ph,
        area_ha=area,
        irrigation_mm=0.0 if water == "rainfed" else mm,
        irrigation_basis="rain only" if water == "rainfed" else basis,
        rain_fraction=fraction,
        pilot_confirmed=confirmed,
    )
    with st.container(horizontal=True):
        if st.button("Continue", type="primary"):
            go("season")
        if st.button("Back"):
            go("location")


def window_picker(label, old=None):
    from .ui_state import capture

    number = 1 if label else 0
    start_key = f"wf_start_{number}"
    end_key = f"wf_end_{number}"
    start_idx = None if start_key in S else (old.start_month - 1 if old else None)
    end_idx = None if end_key in S else (old.end_month - 1 if old else None)
    a, b = st.columns(2)
    sm = a.selectbox(
        "Planting month" + label,
        range(1, 13),
        index=start_idx,
        format_func=lambda m: calendar.month_name[m],
        placeholder="Choose month",
        key=start_key,
        persist_state="session",
        on_change=capture,
    )
    em = b.selectbox(
        "Last growing month" + label,
        range(1, 13),
        index=end_idx,
        format_func=lambda m: calendar.month_name[m],
        placeholder="Choose month",
        key=end_key,
        persist_state="session",
        on_change=capture,
    )
    return Window(sm, 1, em, calendar.monthrange(2023, em)[1]) if sm and em else None


def season():
    from .ui_state import capture
    from .ui_components import context_bar, caption, render_calendar_strip
    from .climate_insights import site_summary, suggest_window

    heading(3)
    d = S.draft
    windows = []
    named = "Farmer-selected months"
    regional = d.get("pilot_confirmed", False)
    old = d.get("windows", ())

    suggestion = None
    if S.dataset is not None and not regional:
        info = site_summary(S.dataset)
        suggestion = suggest_window(info["climatology"], info["growing_period"])
        if suggestion:
            s_m, e_m = suggestion["start_month"], suggestion["end_month"]
            btn_label = f"Use suggested rain-supported season: {calendar.month_name[s_m]} – {calendar.month_name[e_m]} ({suggestion['months']} mo)"
            if st.button(btn_label, key="apply_suggested_season", icon=":material/auto_awesome:"):
                S["wf_start_0"] = s_m
                S["wf_end_0"] = e_m
                old = (Window(s_m, 1, e_m, calendar.monthrange(2023, e_m)[1]),)
                d["windows"] = old
                st.rerun()

    calendars = S.context.get("calendar", {}).get("value") or []
    if calendars:
        with st.expander("Local planting references"):
            st.caption(
                "Choose a crop, then check the named zone. These dates do not select your season."
            )
            calendar_choice = st.selectbox(
                "Published crop calendars",
                calendars,
                index=None,
                format_func=lambda r: r["name"],
            )
            if calendar_choice:
                from .providers import crop_calendars

                cache = S.context.setdefault("planting_dates", {})
                if calendar_choice["id"] not in cache:
                    with st.spinner("Loading published dates…"):
                        cache[calendar_choice["id"]] = crop_calendars(
                            S.point[0], calendar_choice["id"]
                        )
                response = cache[calendar_choice["id"]]
                if response.get("value"):
                    st.dataframe(response["value"], hide_index=True)
                else:
                    st.caption("Planting dates are unavailable for this crop.")
    if regional:
        choices = ["Yala then Maha", "Maha then Yala", "Choose my months"]
        named = st.selectbox(
            "Growing seasons",
            choices,
            index=(
                choices.index(d["season_name"])
                if d.get("season_name") in choices
                else None
            ),
            placeholder="Choose the seasons for this field",
            key="wf_season_name",
            persist_state="session",
            on_change=capture,
        )
        if named in ("Yala then Maha", "Maha then Yala"):
            from .assistant import SEASON_TEMPLATES

            windows = list(SEASON_TEMPLATES[named]["windows"])
            st.caption("Then ".join(w.label + " " for w in windows).strip())
    if not regional or named == "Choose my months":
        windows = [window_picker("", old[0] if old else None)]
        if regional:
            windows.append(
                window_picker(" · second season", old[1] if len(old) > 1 else None)
            )
    render_calendar_strip(S.dataset, windows[0] if windows and windows[0] else (old[0] if old else None))
    from .knowledge import search_crops, count_crops, crop_by_id

    query = (
        st.text_input("Search previous crop", placeholder="Start a crop name")
        if count_crops() > 50
        else ""
    )
    from .soil_and_water import format_crop_with_local_name

    cc_cur = S.point[0] if S.point else ""
    crops = {
        r["id"]: format_crop_with_local_name(r["id"], r["name"], cc_cur)
        for r in search_crops(query, limit=250)
    }
    if d.get("current", "unknown") not in ("unknown", *crops):
        saved = crop_by_id(d["current"])
        if saved:
            crops[saved["id"]] = format_crop_with_local_name(
                saved["id"], saved["name"], cc_cur
            )
    history = {"unknown": "Not sure / first crop", **crops}
    current = choice("Last crop grown here", history, d, "current")
    baseline = ()
    cultivar = "unknown"
    if regional:
        with st.expander("Rotation options"):
            cultivar = st.selectbox(
                "Mung bean variety",
                ["unknown", "MI 6", "other"],
                index=["unknown", "MI 6", "other"].index(
                    d.get("mung_cultivar", "unknown")
                ),
                format_func=lambda x: "Not sure" if x == "unknown" else x,
                key="wf_mung_cultivar",
                persist_state="session",
                on_change=capture,
            )
            include = st.checkbox(
                "Compare with my existing plan",
                value=bool(d.get("baseline")),
                key="wf_include_baseline",
                persist_state="session",
                on_change=capture,
            )
            if include:
                old_base = d.get("baseline") or ()
                pair = [
                    st.selectbox(
                        label,
                        list(CROPS),
                        index=list(CROPS).index(old_base[i]) if old_base else None,
                        format_func=lambda k: CROPS[k]["name"],
                        key=f"wf_planned_{i}",
                        persist_state="session",
                        on_change=capture,
                    )
                    for i, label in enumerate(
                        ["Planned first crop", "Planned second crop"]
                    )
                ]
                if all(pair):
                    baseline = tuple(pair)
    S.draft.update(
        season_name=named,
        windows=tuple(windows),
        current=current,
        baseline=baseline,
        mung_cultivar=cultivar,
    )
    with st.expander("Review your field", expanded=True, key="field_review"):
        known_ph = "Unknown" if d.get("ph") is None else f"{d['ph']:g} (measured)"
        context_bar(
            [
                ("Location", S.point[3]),
                ("Water", WATER.get(d.get("irrigation"), "Not sure")),
                ("Soil pH", known_ph),
                ("Drainage", DRAIN.get(d.get("drainage"), "Not sure")),
            ]
        )
        caption(
            "NASA historical grid estimates are ready. Crop requirements come from published references."
        )
    if st.button(
        "Find crop options",
        type="primary",
        disabled=not windows
        or not all(windows)
        or (regional and include and not baseline),
    ):
        cc, lat, lon, _ = S.point
        farm = Farm(
            latitude=lat,
            longitude=lon,
            country=cc,
            input_origin=(
                "edited demonstration profile" if S.demo_active else "farm profile"
            ),
            **S.draft,
        )
        try:
            finish(farm)
        except (DataError, ValueError) as e:
            st.error(str(e))
    if st.button("Back"):
        go("conditions")
