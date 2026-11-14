"""Research tools are loaded only when selected; the farmer's home makes no API calls."""

from dataclasses import replace
from datetime import date
import json
import pandas as pd
import streamlit as st
from .decision import assess, CRITERIA, CROPS, priority_sensitivity
from .climate import aggregate
from .finder_ui import S, cc_name, go, start, demo, WATER, DRAIN
from .geography import pilot_scope
from .locations import load_history
from .power import DataError

TOPICS = [
    "Crop catalogue",
    "Climate history",
    "Soil information",
    "Maps",
    "Rotation comparison",
    "What-if scenarios",
    "Data sources",
    "Downloads",
    "Ask about my results",
    "Learning lab",
]

TOPIC_LABELS = {
    "Ask about my results": "Ask about my results — Plain-language Q&A & AI summary",
    "Climate history": "Climate history — Seasonal rainfall, heat & dry spells",
    "Soil information": "Soil information — Soil pH, texture & root-zone water",
    "Maps": "Maps — Satellite view of your field & boundary",
    "Crop catalogue": "Crop catalogue — Browse 107 crops & growing needs",
    "Downloads": "Downloads — Save or print your farm report & weather CSV",
    "Rotation comparison": "Rotation comparison — Two-season crop sequence planner",
    "What-if scenarios": "What-if scenarios — Test drought, heat or extra irrigation",
    "Learning lab": "Learning lab — Seasonal outlook & similar past years",
    "Data sources": "Data sources — Satellite, market prices, terrain & soil records",
}

TOPIC_GUIDES = {
    "Ask about my results": (
        "Plain-Language Farm Q&A & AI Brief",
        "Ask everyday questions about why certain crops fit your farm, why others say 'Check before planting', how your soil pH or water affects your choices, or generate an executive summary.",
    ),
    "Climate history": (
        "25-Year Local Weather & Rainfall Guide",
        "See which months receive enough rain for rainfed crops (green shaded bars) and how warm or dry your location normally gets across 25 years of NASA satellite records.",
    ),
    "Soil information": (
        "Field Soil pH, Texture & Water-Holding Guide",
        "Understand your soil's acidity (pH), texture (clay/sand/loam), and how much water the root zone can store between rains or irrigations.",
    ),
    "Maps": (
        "Interactive Field & Satellite Map",
        "Inspect your farm location and drawn field boundary on Sentinel-2 cloudless satellite imagery and OpenStreetMap terrain.",
    ),
    "Crop catalogue": (
        "Reference Guide to 107 Crops",
        "Look up temperature, rainfall, soil pH, and growing-season requirements for 107 food and cash crops from FAO and regional agronomy handbooks.",
    ),
    "Downloads": (
        "Save, Print, or Share Your Farm Plan",
        "Download a clean, printable Farmer Report (HTML) to take to the field or extension officer, or export raw JSON/CSV records.",
    ),
    "Rotation comparison": (
        "Two-Season Crop Rotation Planner",
        "Compare two-season crop combinations (such as Rice followed by Mungbean, Cowpea, or Maize) to balance water risk, heat tolerance, and soil health.",
    ),
    "What-if scenarios": (
        "Farm Stress-Test Simulator (What-If)",
        "Test what happens to your crop options if rainfall drops during a dry monsoon, temperatures rise, or you add supplemental irrigation or lime.",
    ),
    "Learning lab": (
        "Seasonal Outlook & Historical Analog Years",
        "Explore next-season rainfall/temperature forecast ranges (90% conformal intervals) and see which past years had weather most similar to your field.",
    ),
    "Data sources": (
        "Verified Satellite, Market & Regional References",
        "Check local WFP food price benchmarks, Copernicus 90m terrain slope, FAO WaPOR evapotranspiration, ESA WorldCereal cropland maps, and crop calendars.",
    ),
}


def need_weather():
    if S.dataset is None:
        st.info("Choose a location to see its historical weather.")
        if st.button("Choose location", type="primary"):
            start("climate")
        if st.button("Use an example farm"):
            demo()
        st.stop()
    return S.dataset


def regional():
    f = S.farm
    return (
        f
        and len(f.windows) == 2
        and pilot_scope(f.latitude, f.longitude, f.country, f.pilot_confirmed)
    )


@st.fragment
def catalogue():
    from .knowledge import (
        search_crops,
        knowledge_status,
        count_crops,
        crop_categories,
        global_traits,
    )
    from .crop_search import crop_query
    from .ui_components import SUPPORT, caption
    from html import escape

    q = crop_query()
    category = st.selectbox(
        "Crop category",
        [None, *crop_categories()],
        format_func=lambda x: x or "All categories",
        key="catalogue_category",
        persist_state="session",
    )
    total = count_crops(q, category=category)
    page = (
        st.number_input(
            "Catalogue page",
            min_value=1,
            max_value=max(1, (total + 9) // 10),
            value=1,
            step=1,
            key="catalogue_page_" + q + str(category),
        )
        if total > 10
        else 1
    )
    rows = search_crops(q, limit=10, offset=(page - 1) * 10, category=category)
    if not rows:
        st.info("No matching crops. Try another name or choose All categories.")
        return
    caption(
        f"{total} matching crops · catalogue names are not planting recommendations."
    )
    for r in rows:
        with st.expander(
            r["name"] + " · " + SUPPORT.get(r["support_level"], r["support_level"])
        ):
            st.write(r.get("scientific_name") or "Scientific name not recorded")
            caption(r.get("group_name") or "Category not recorded")
            if r["support_level"] == "catalogue":
                st.write(
                    "This crop has a catalogue entry, but no reviewed screening thresholds in this release."
                )
            else:
                st.write(
                    "Published references are available. Their applicability depends on location and field information."
                )
            traits = global_traits(r["id"])
            for t in traits:
                st.write(
                    f'**{t["trait"].replace("_", " ").title()}** · {t["low"]}–{t["high"]} {t["units"]}'
                )
                st.markdown(f'[{t["source_title"]}]({t["source_url"]})')
                caption(
                    f'{t["evidence_type"]} · {t["scope"]} · retrieved {t["retrieved_on"] or "date not recorded"}'
                )
                caption(t["note"])
            if r.get("family_reference"):
                st.markdown(
                    f'[Botanical classification source]({r["family_reference"]})'
                )
            if r.get("concept_uri"):
                st.markdown(f'[Catalogue identity]({r["concept_uri"]})')
    with st.expander("Catalogue source"):
        info = knowledge_status()
        st.write("Serving catalogue from: " + str(info["backend"]))
        if info.get("fallback_reason"):
            st.caption(
                "Hosted catalogue unavailable; the bundled reference database is in use."
            )


def climate():
    from .ui_components import (
        build_climograph_figure,
        render_calendar_strip,
        render_site_intelligence_banner,
    )

    ds = need_weather()
    st.subheader(S.point[3], anchor=False)
    p = ds.provenance
    st.caption(
        f"NASA POWER · {p['request']['start'][:4]}–{p['request']['end'][:4]} · {p['mode']}"
    )
    render_site_intelligence_banner(ds, S.context, S.point)
    measure = st.radio(
        "Show historical",
        [
            "Combined climograph (Rain, ET₀ & Temp)",
            "Rainfall",
            "Temperature",
            "Solar energy",
        ],
        horizontal=True,
    )
    monthly = aggregate(ds.frame)
    k = {
        "Combined climograph (Rain, ET₀ & Temp)": "rainfall_mm",
        "Rainfall": "rainfall_mm",
        "Temperature": "temperature_c",
        "Solar energy": "solar_mj_m2_day",
    }[measure]
    data = monthly[k].groupby(monthly.index.month).mean().reindex(range(1, 13))
    if data.notna().any():
        fig = build_climograph_figure(ds, measure)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        render_calendar_strip(ds, S.farm.windows[0] if S.farm and S.farm.windows else None)
    else:
        st.info("There are no complete observations for this measure.")
    st.caption(
        "Monthly averages across the selected years. Shaded columns mark months where mean rainfall meets at least half of reference evapotranspiration (FAO LGP rule). Historical grid estimates, not a forecast."
    )
    with st.expander("Coverage and weather data"):
        st.dataframe(
            pd.DataFrame(
                {"Series": ds.frame.columns, "Days with data": list(ds.frame.count())}
            ),
            hide_index=True,
        )
        for note in ds.issues:
            st.write(note)
        st.json(
            {
                k: p[k]
                for k in (
                    "source",
                    "product",
                    "url",
                    "retrieved_at_utc",
                    "sha256",
                    "units",
                    "meteorology_grid",
                    "solar_grid",
                )
            }
        )
        st.download_button(
            "Download weather CSV",
            ds.frame.to_csv(),
            "agroshift-weather.csv",
            "text/csv",
            on_click="ignore",
        )
    with st.expander("Change weather years"):
        a, b = st.columns(2)
        y1 = a.number_input(
            "First year",
            1981,
            date.today().year - 1,
            value=int(p["request"]["start"][:4]),
        )
        y2 = b.number_input(
            "Last year", 1981, date.today().year - 1, value=int(p["request"]["end"][:4])
        )
        if st.button("Load these years"):
            try:
                with st.spinner("Loading historical weather…"):
                    new = load_history(S.point[1], S.point[2], y1, y2, refresh=True)
                from .screening import find_options

                cards = find_options(S.farm, new, weights=S.weights) if S.farm else []
                S.dataset = new
                S.cards = cards
                st.rerun()
            except DataError as e:
                st.error(
                    f"Could not apply these years. Current weather is unchanged. {e}"
                )
    if st.button("Change location"):
        start("climate")


def priorities():
    with st.expander("Adjust priorities"):
        new = {
            k: st.slider(t, 0, 100, int(S.weights[k]), key="priority_" + k)
            for k, t in zip(
                CRITERIA,
                ["Temperature", "Water", "Soil and drainage", "Crop family changes"],
            )
        }
    if not sum(new.values()):
        st.warning("Set at least one priority above zero.")
        st.stop()
    if new != S.weights:
        from .screening import find_options

        cards = find_options(S.farm, S.dataset, weights=new)
        S.weights = new
        S.cards = cards


def rotations(scenario=False):
    ds = need_weather()
    if not regional():
        st.info(
            "Two-season rotations need a confirmed Sri Lankan lowland dry or intermediate field. General crop checks are available in Crop Finder."
        )
        if st.button("Open example farm"):
            demo()
        if S.farm is not None and not scenario:
            from .decision import Window
            from .rotation_engine import plan_global_rotations

            st.subheader("International Botanical Rotation Explorer", anchor=False)
            st.caption(
                "Explore two-season botanical family alternation, rooting-depth diversity, and legume succession for your location (published global references, not regional yield rankings)."
            )
            w1 = S.farm.windows[0]
            if len(S.farm.windows) >= 2:
                farm_rot = S.farm
            else:
                s2_m = (w1.end_month % 12) + 1
                e2_m = ((s2_m + 2) % 12) + 1
                w2 = Window(s2_m, 1, e2_m, 28)
                farm_rot = replace(S.farm, windows=(w1, w2))
            seqs = plan_global_rotations(farm_rot, ds, max_sequences=12)
            if seqs:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Sequence": s["name"],
                                "Season 1 (" + s["season_1"]["window"] + ")": f"{s['season_1']['crop_name']} ({s['season_1']['family'] or '—'})",
                                "Season 2 (" + s["season_2"]["window"] + ")": f"{s['season_2']['crop_name']} ({s['season_2']['family'] or '—'})",
                                "Rotation Fit": s["summary"],
                                "Status": s["overall_status"].title(),
                            }
                            for s in seqs
                        ]
                    ),
                    hide_index=True,
                )
                with st.expander("Botanical rotation benefits and cautions"):
                    for s in seqs[:6]:
                        notes = s["transition"]["benefits"] + s["transition"]["cautions"] + s["transition"]["blockers"]
                        if notes:
                            st.write(f"**{s['name']}** ({s['summary']}): " + " ".join(notes))
                    st.caption(seqs[0]["transition"]["scientific_disclaimer"])
        return
    priorities()
    f = S.farm
    base = assess(ds.frame, f, S.weights)
    rows = base
    if scenario:
        st.caption(
            "Change an assumption to compare it with the recorded farm. Your field stays unchanged."
        )
        drainage = st.selectbox(
            "Drainage",
            list(DRAIN),
            index=list(DRAIN).index(f.drainage),
            format_func=DRAIN.get,
        )
        a, b = st.columns(2)
        rain = a.slider("Rainfall (% of history)", 0, 200, 100, 5) / 100
        temp = b.slider("Temperature change (°C)", -5.0, 5.0, 0.0, 0.5)
        with st.expander("Change water or soil"):
            ph = st.number_input("Scenario pH", 0.0, 14.0, value=f.ph)
            mm = st.number_input(
                "Scenario net irrigation (mm)", min_value=0.0, value=f.irrigation_mm
            )
            frac = st.number_input(
                "Scenario usable rain fraction", 0.0, 1.0, value=f.rain_fraction
            )
        f = replace(
            f,
            drainage=drainage,
            ph=ph,
            irrigation_mm=mm,
            rain_fraction=frac,
            irrigation="supplemental" if mm and mm > 0 else f.irrigation,
            irrigation_basis="illustrative scenario",
        )
        rows = assess(ds.frame, f, S.weights, rain, temp)
        orig = {r["id"]: r for r in base}
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Rotation": r["name"],
                        "Original": orig[r["id"]]["status"],
                        "Scenario": r["status"],
                        "Original range": interval(orig[r["id"]]),
                        "Scenario range": interval(r),
                    }
                    for r in rows
                ]
            ),
            hide_index=True,
        )
        from .reporting import report_html

        st.download_button(
            "Save scenario",
            report_html(
                ds, f, S.weights, rows, dict(rain_factor=rain, temp_delta=temp)
            ),
            "agroshift-scenario.html",
            "text/html",
            on_click="ignore",
        )
        return
    st.caption(
        "Preference ranges reflect missing evidence. Overlapping ranges do not establish a winner."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Rotation": r["name"],
                    "Preference interval": interval(r),
                    "Status": r["status"],
                }
                for r in rows
            ]
        ),
        hide_index=True,
    )
    chosen = st.selectbox(
        "Inspect a rotation", range(len(rows)), format_func=lambda i: rows[i]["name"]
    )
    for t in rows[chosen]["constraints"]:
        st.warning(t)
    with st.expander("Evidence by factor"):
        for k, v in rows[chosen]["components"].items():
            st.write("**" + k.title() + ":** " + v["reason"])
        st.dataframe(
            pd.DataFrame(priority_sensitivity(rows, S.weights)), hide_index=True
        )
    from .soil_and_water import compute_uncertainty_narrowing_guide

    voi = compute_uncertainty_narrowing_guide(ds.frame, f, S.weights)
    if voi.get("available") and voi.get("actions"):
        with st.expander("Value-of-Information (VoI) Uncertainty Narrowing Guide"):
            st.caption(
                f"Current lead rotation preference interval width: ±{voi['current_width']:.1f} pts ({voi['evidence_coverage_pct']:.0f}% weight assessed)."
            )
            for act in voi["actions"]:
                st.write(f"**{act['title']}** — Narrows interval by up to **±{act['impact_pts']:.1f} pts**")
                st.caption(f"{act['explanation']} ({act['suggested_label']})")


def interval(r):
    return f"{r['low']:.1f}–{r['high']:.1f}"


def downloads():
    ds = need_weather()
    if S.farm:
        from .finder_report import make_record, readable

        record = make_record(ds, S.farm, S.cards, S.weights, S.get("context"))
        st.subheader("Crop Finder results", anchor=False)
        with st.container(horizontal=True):
            st.download_button(
                "Farmer report",
                readable(record),
                "agroshift-crops.html",
                "text/html",
                on_click="ignore",
            )
            st.download_button(
                "Crop data (JSON)",
                json.dumps(record, indent=2, allow_nan=False),
                "agroshift-crops.json",
                "application/json",
                on_click="ignore",
            )
        if regional():
            from .reporting import report_html, report_json

            rows = assess(ds.frame, S.farm, S.weights)
            with st.expander("Full rotation analysis"):
                st.download_button(
                    "Rotation report",
                    report_html(ds, S.farm, S.weights, rows),
                    "agroshift-rotations.html",
                    "text/html",
                    on_click="ignore",
                )
                st.download_button(
                    "Rotation data (JSON)",
                    report_json(ds, S.farm, S.weights, rows),
                    "agroshift-rotations.json",
                    "application/json",
                    on_click="ignore",
                )
    st.download_button(
        "Daily weather (CSV)",
        ds.frame.to_csv(),
        "agroshift-weather.csv",
        "text/csv",
        on_click="ignore",
    )


def sources(selected=None):
    from .providers import (
        provider_registry,
        soil_context,
        national_production,
        gaez_context,
        terminology,
        calendar_crops,
        crop_calendars,
    )

    source = selected or st.selectbox(
        "Look up",
        [
            "Source directory",
            "Soil estimate",
            "Crop calendar",
            "National production",
            "GAEZ country context",
            "Terrain & drainage slope (Copernicus DEM)",
            "Seasonal climate outlook (ECMWF SEAS5)",
            "Satellite ET & biomass (FAO WaPOR v3)",
            "Active cropland & irrigation prior (ESA WorldCereal 10m)",
            "CHIRPS satellite rainfall benchmark (5.5 km)",
            "WFP market price benchmarks",
            "Crop terminology",
        ],
    )
    if source == "Source directory":
        from .farm_ui import capability_view

        with st.expander("What can this location support?"):
            capability_view()
        for r in provider_registry():
            with st.expander(r["name"]):
                st.write(r["detail"])
                st.caption(r["status"])
                if r.get("source", "").startswith("https://"):
                    st.markdown(f'[Provider website]({r["source"]})')
        return
    from .finder_ui import cc_name

    if source == "Crop terminology":
        term = st.text_input("Crop name", value="maize")
        lang = st.selectbox("Language", ["en", "fr", "es"])
        fn = lambda: terminology(term, lang)
    else:
        if S.point is None:
            st.info("Choose a location to look up its sources.")
            if st.button("Choose location"):
                start("climate")
            return
        cc, lat, lon, where = S.point
        st.caption(f"{where} · {cc_name(cc)}")
        if source == "Soil estimate":
            from html import escape as _esc
            from .soil_and_water import detect_sri_lanka_aer, fetch_soil_profile

            sp = fetch_soil_profile(lat, lon, allow_network=False)
            aer = detect_sri_lanka_aer(lat, lon)
            hyd = sp["hydraulics"]
            user_ph = S.farm.ph if S.farm and S.farm.ph is not None else None
            ph_val = user_ph if user_ph is not None else sp["ph_median"]
            ph_band = (
                "Acidic (good for rice, tea, potato, cassava; legumes may benefit from lime)"
                if ph_val < 5.6
                else (
                    "Slightly acidic to neutral (ideal for most grains, pulses, and vegetables)"
                    if ph_val <= 7.2
                    else "Slightly alkaline (monitor micronutrients for sensitive crops)"
                )
            )
            aer_html = (
                f'<div><small>Sri Lanka Agro-Ecological Zone</small><strong>{_esc(aer["aer_code"])} · {_esc(aer["great_soil_group"])}</strong></div>'
                if aer.get("in_sri_lanka")
                else ""
            )
            st.html(
                f'<div class="ag-context-bar" style="margin-bottom:0.75rem">'
                f'<div><small>{"Your Measured Soil pH" if user_ph is not None else "Regional Topsoil pH Reference"}</small>'
                f'<strong>pH {ph_val:.1f}</strong> <span style="font-size:0.82rem;opacity:0.85">({_esc(ph_band)})</span></div>'
                f'<div><small>Typical Soil Texture</small><strong>{_esc(sp["usda_texture"].replace("_", " ").title())}</strong> '
                f'<span style="font-size:0.82rem;opacity:0.85">(Clay {sp["clay_pct"]:.0f}%, Sand {sp["sand_pct"]:.0f}%)</span></div>'
                f'<div><small>Root-Zone Water Storage</small><strong>~{hyd["awc_mm_per_m"]:.0f} mm per meter</strong> '
                f'<span style="font-size:0.82rem;opacity:0.85">(Field capacity {hyd["field_capacity_vol_pct"]:.0f}%)</span></div>'
                f"{aer_html}"
                f"</div>"
            )
            st.write("A regional map estimate is a helpful starting point, but a soil test or pH strip check on your own field always takes precedence.")
            fn = lambda: soil_context(lat, lon)
        elif source == "Crop calendar":
            st.caption(
                "Calendars apply to the named zone and crop. Confirm your planting dates locally."
            )
            fn = lambda: calendar_crops(cc)
        elif source == "National production":
            st.caption("Country totals do not predict the harvest on this farm.")
            fn = lambda: national_production(cc)
        elif source == "Terrain & drainage slope (Copernicus DEM)":
            from .providers import terrain_context

            st.caption("90 m Copernicus DEM elevation, regional slope, and local drainage relief proxy.")
            fn = lambda: terrain_context(lat, lon)
        elif source == "Seasonal climate outlook (ECMWF SEAS5)":
            from .providers import seasonal_outlook_context

            st.caption(
                "Forward-looking ~36 km seasonal ensemble outlook (Open-Meteo / ECMWF SEAS5). Strictly isolated from historical crop screening."
            )
            fn = lambda: seasonal_outlook_context(lat, lon)
        elif source == "Satellite ET & biomass (FAO WaPOR v3)":
            from .soil_and_water import wapor_water_productivity_context

            st.caption(
                "FAO WaPOR v3 (300 m dekadal) Actual Evapotranspiration (AETI) and Biomass Water Productivity reference."
            )
            fn = lambda: wapor_water_productivity_context(lat, lon)
        elif source == "Active cropland & irrigation prior (ESA WorldCereal 10m)":
            from .soil_and_water import worldcereal_cropland_context

            st.caption(
                "ESA WorldCereal 10 m active cropland and seasonal irrigation reference prior."
            )
            fn = lambda: worldcereal_cropland_context(lat, lon)
        elif source == "CHIRPS satellite rainfall benchmark (5.5 km)":
            from .providers import chirps_context

            st.caption(
                "UCSB CHG CHIRPS v2.0 0.05° (~5.5 km) quasi-global satellite-gauge rainfall benchmark (strictly independent from NASA POWER)."
            )
            fn = lambda: chirps_context(lat, lon)
        elif source == "WFP market price benchmarks":
            from .soil_and_water import market_price_context

            st.caption(
                "WFP VAM / HDX Food Prices Monitor contextual market benchmarks (retail/wholesale signal only, not a farm-gate guarantee)."
            )
            fn = lambda: market_price_context(cc)
        else:
            st.caption("National land-model estimates do not predict farm yield.")
            fn = lambda: gaez_context(cc)
    # Reuse automatic context only when it matches this exact location.
    auto = S.context if S.point and S.context.get("point") == list(S.point[:3]) else {}
    auto_record = auto.get(
        {"Soil estimate": "soil", "Crop calendar": "calendar"}.get(source, "")
    )
    context = (
        source,
        S.point,
        term if source == "Crop terminology" else None,
        lang if source == "Crop terminology" else None,
    )
    if st.button("Look up data"):
        with st.spinner("Checking source…"):
            S.provider_view = (context, fn())
    selected_record = (
        S.provider_view[1]
        if S.get("provider_view") and S.provider_view[0] == context
        else auto_record
    )
    if selected_record:
        rec = selected_record
        st.write(rec["detail"])
        if rec.get("value") is not None:
            if source == "Crop calendar" and rec["value"]:
                chosen = st.selectbox(
                    "Crop calendar", rec["value"], format_func=lambda r: r["name"]
                )
                if st.button("Show planting dates"):
                    res = crop_calendars(cc, chosen["id"])
                    if res.get("value"):
                        st.dataframe(pd.DataFrame(res["value"]), hide_index=True)
                    st.caption(res["detail"])
            elif source == "Soil estimate":
                st.metric("Modelled topsoil pH", str(rec["value"]))
                from .soil import reconcile_soil_evidence

                reconciled = reconcile_soil_evidence(
                    S.farm.ph if S.farm else None, rec
                )
                st.caption(reconciled["precedence_note"])
                if reconciled["disagreement"].get("summary"):
                    if reconciled["disagreement"].get("meaningful_disagreement"):
                        st.warning(reconciled["disagreement"]["summary"], icon=":material/science:")
                    else:
                        st.info(reconciled["disagreement"]["summary"], icon=":material/check_circle:")
            elif isinstance(rec["value"], list):
                st.dataframe(pd.DataFrame(rec["value"]), hide_index=True)
            else:
                st.write(rec["value"])
        with st.expander("Retrieval details"):
            st.json({k: v for k, v in rec.items() if k != "value"})


def assistant():
    ds = need_weather()
    if not S.farm:
        st.info("Run Crop Finder to ask about your results.")
        return
    from .assistant import answer_farmer_question, query_optional_gemini

    q = st.text_input(
        "What would you like to understand?",
        placeholder="For example: Which crops fit my farm best, or how does soil pH affect my options?",
    )
    st.caption("Or tap a common farmer question below:")
    q_cols = st.columns(2)
    for idx, prompt_label in enumerate(
        (
            "Which crops fit my farm best right now, and why?",
            "Why are some crops marked check before planting?",
            "How does soil pH affect my crop options?",
            "What is still unknown about water?",
            "What is the historical rainfall and temperature range?",
            "How can I narrow uncertainty in my farm results?",
        )
    ):
        if q_cols[idx % 2].button(prompt_label, key=f"suggest_q_{idx}"):
            S["assistant_active_q"] = prompt_label
    if q:
        S["assistant_active_q"] = q
    active_q = (
        q
        or S.get("assistant_active_q")
        or "Which crops fit my farm best right now, and why?"
    )
    if active_q:
        rows = assess(ds.frame, S.farm, S.weights) if regional() else []
        res = answer_farmer_question(
            active_q, ds, S.farm, S.weights, rows, cards=S.cards
        )
        st.caption(f"Showing explanation for: **{active_q}**")
        st.markdown(res["answer"])
        with st.expander("Sources and optional Gemini summary", expanded=True):
            st.markdown("**Optional Gemini AI Executive Brief**")
            key = st.text_input(
                "Optional Gemini API key",
                value=S.get("gemini_api_key", ""),
                type="password",
                help="Paste a Google AI Studio (Gemini) API key to select and format relevant brief topics, or leave blank to use the built-in verified executive summary.",
            )
            if key:
                S["gemini_api_key"] = key
            st.caption(
                "Your question and verified farm facts are used to compile a concise executive brief without inventing unverified yield or profit claims."
            )
            if st.button("Request summary", type="primary"):
                try:
                    gem_text = query_optional_gemini(active_q, res["brief"], key)
                    st.success("Verified Gemini Executive Summary:")
                    st.markdown(gem_text)
                except DataError as exc:
                    sc = res["brief"].get("screened_crops", {})
                    fallback_lines = [
                        sc.get("worth_considering_summary", ""),
                        sc.get("check_before_planting_summary", ""),
                        sc.get("climate_summary", ""),
                        sc.get("soil_summary", ""),
                        sc.get("next_steps_summary", ""),
                    ]
                    st.info(
                        f"{exc} Showing the built-in verified executive summary for your farm below:"
                    )
                    st.markdown("\n\n".join(x for x in fallback_lines if x))
            st.markdown("**Scientific & Data Citations**")
            for r in res["citations"]:
                st.markdown(f'- [{r["title"]}]({r["url"]})')
    if regional():
        from .assistant import run_counterfactual_copilot

        with st.expander("Counterfactual Stress & Management Simulator"):
            st.caption(
                "Test how supplying missing soil/water inputs or experiencing a severe monsoon drought shifts the rotation preference intervals."
            )
            cf_cols = st.columns(3)
            cf_choice = None
            for idx_cf, (cf_key, cf_btn) in enumerate(
                (
                    ("apply_soil_and_upland_water", "SoilGrids Prior + 180 mm Water"),
                    ("severe_drought_heat", "-25% Rain & +1.5 °C Heat"),
                    ("waterlogged_paddy_basin", "Waterlogged Paddy Basin"),
                )
            ):
                if cf_cols[idx_cf].button(cf_btn, key=f"cf_sim_{cf_key}"):
                    cf_choice = cf_key
            if cf_choice:
                cf_out = run_counterfactual_copilot(cf_choice, ds, S.farm, S.weights)
                st.write(f"**{cf_out['label']}**")
                st.caption(
                    f"Lead sequence: **{cf_out['baseline_lead']}** ({cf_out['baseline_interval'][0]:.1f}–{cf_out['baseline_interval'][1]:.1f}) "
                    f"→ **{cf_out['counterfactual_lead']}** ({cf_out['counterfactual_interval'][0]:.1f}–{cf_out['counterfactual_interval'][1]:.1f}) "
                    f"· Interval width delta: **{cf_out['width_change_pts']:+.1f} pts**"
                )
                st.dataframe(pd.DataFrame(cf_out["table"]), hide_index=True)


def maps():
    if S.point is None:
        st.info("Choose a field to explore its location.")
        if st.button("Choose location", type="primary"):
            start("climate")
        return
    st.caption(
        "Field location · Sentinel-2 cloudless (EOX / Copernicus 2016, CC BY 4.0) & OpenStreetMap. Environmental estimates use the selected point."
    )
    from streamlit_folium import st_folium
    from .ui_components import satellite_map

    m = satellite_map(
        S.point[1],
        S.point[2],
        zoom=12,
        label=S.point[3],
        boundary=S.boundary,
    )
    st_folium(
        m, height=420, use_container_width=True, returned_objects=[], key="explore_map"
    )
    st.caption(
        "Crop-specific FAO land-model comparisons are available in crop details where supported."
    )
    if S.farm and st.button("Manage field boundary"):
        go("my_farm")


def render():
    from html import escape as _esc
    from .ui_components import page_heading

    page_heading(
        "Explore",
        "Plain-language farm explanations, local weather & soil guides, and planning tools.",
    )
    if S.farm and S.cards:
        worth_n = sum(1 for c in S.cards if c.get("status") == "possible")
        check_n = sum(1 for c in S.cards if c.get("status") == "check")
        loc_lbl = S.point[3] if S.point else S.farm.country
        win_lbl = S.farm.windows[0].label if S.farm.windows else "Selected season"
        st.html(
            f'<div class="ag-context-bar" style="margin-bottom:0.65rem">'
            f'<div><small>Active Farm</small><strong>{_esc(str(loc_lbl))}</strong> ({_esc(str(win_lbl))})</div>'
            f'<div><small>Worth Considering</small><strong>{worth_n} crop{"s" if worth_n != 1 else ""}</strong></div>'
            f'<div><small>Check Before Planting</small><strong>{check_n} crop{"s" if check_n != 1 else ""}</strong></div>'
            f"</div>"
        )
    topic = st.selectbox(
        "Explore topic",
        TOPICS,
        index=TOPICS.index(S.section),
        format_func=lambda t: TOPIC_LABELS.get(t, t),
        key="research_choice",
        persist_state="session",
    )
    S.section = topic
    cat1_active = (
        " as-hub-cat-active"
        if topic in ("Ask about my results", "Crop catalogue", "Downloads", "Data sources")
        else ""
    )
    cat2_active = (
        " as-hub-cat-active"
        if topic in ("Climate history", "Soil information", "Maps")
        else ""
    )
    cat3_active = (
        " as-hub-cat-active"
        if topic in ("Rotation comparison", "What-if scenarios", "Learning lab")
        else ""
    )
    st.html(
        f'<div class="as-explore-hub">'
        f'<div class="as-hub-cat{cat1_active}"><small>01 · Field Q&amp;A &amp; Reports</small>'
        f"<strong>Ask Questions, Crop Guide &amp; Reports</strong>"
        f"<span>Plain-language Q&amp;A, crop requirements, and printable farm summaries</span></div>"
        f'<div class="as-hub-cat{cat2_active}"><small>02 · Weather, Soil &amp; Satellite Map</small>'
        f"<strong>Rainfall, Soil Water &amp; Maps</strong>"
        f"<span>Local rainfall history, root-zone soil moisture, and map layers</span></div>"
        f'<div class="as-hub-cat{cat3_active}"><small>03 · Rotations, What-If &amp; Forecasts</small>'
        f"<strong>Next-Season Planning &amp; Forecasts</strong>"
        f"<span>Crop rotation checks, dry/hot season simulations, and yield forecasts</span></div>"
        f"</div>"
    )
    guide = TOPIC_GUIDES.get(topic)
    if guide:
        st.html(
            f'<div class="ag-card" style="padding:0.75rem 1rem;margin-bottom:0.85rem;border-left:4px solid #2e6b34">'
            f'<div style="font-weight:600;font-size:0.96rem;margin-bottom:0.2rem">{_esc(guide[0])}</div>'
            f'<div style="font-size:0.88rem;opacity:0.9">{_esc(guide[1])}</div>'
            f"</div>"
        )
    if topic == "Learning lab":
        from .education_ui import render as lab

        lab()
    else:
        {
            "Crop catalogue": catalogue,
            "Climate history": climate,
            "Soil information": lambda: sources("Soil estimate"),
            "Maps": maps,
            "Rotation comparison": rotations,
            "What-if scenarios": lambda: rotations(True),
            "Data sources": sources,
            "Downloads": downloads,
            "Ask about my results": assistant,
        }[topic]()
