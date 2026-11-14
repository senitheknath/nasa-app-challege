"""Farmer results and comparison; all findings come from the scientific engine."""

from html import escape
import streamlit as st
from .finder_ui import S, go, research
from .ui_components import (
    SUPPORT,
    ASSESSED,
    badge,
    caption,
    context_bar,
    crop_group_kind,
    crop_icon,
    factors,
    finding_list,
    missing_text,
    page_heading,
    downloads,
    render_evidence_layers_card,
    render_gaez_dual_card,
    render_results_summary_strip,
    render_sowing_heatmap_matrix,
    render_stage_water_chart,
    render_trait_visual_bars,
    render_weather_extremes_strip,
    render_voi_uncertainty_card,
    render_comparison_trait_table,
)


def scope_line():
    context_bar(
        [
            (
                "Farm",
                "Example field" if S.demo_active else S.farm_name or "Selected field",
            ),
            ("Location", S.point[3]),
            ("Growing season", S.farm.windows[0].label),
            ("Climate data", "Historical grid estimates"),
        ]
    )


def open_detail(card):
    S.detail_id = card["id"]
    S.detail_from = S.page
    go("details")


def toggle_comparison(identifier):
    ids = list(S.comparison_ids)
    if identifier in ids:
        ids.remove(identifier)
    elif len(ids) < 3:
        ids.append(identifier)
    S.comparison_ids = ids
    S.pop("compare_ids", None)


def compare_action(r):
    selected = r["id"] in S.comparison_ids
    st.button(
        "Remove" if selected else "Compare",
        key="select_" + r["id"],
        help=(
            ("Remove " if selected else "Add ") + r["name"] + " from comparison"
            if selected
            else "Compare " + r["name"]
        ),
        disabled=not selected and len(S.comparison_ids) >= 3,
        on_click=toggle_comparison,
        args=(r["id"],),
        icon=":material/check:" if selected else ":material/add:",
    )


def card_view(r):
    from .climate_insights import previous_crop_rotation_badge

    with st.container(border=True, key="crop_" + r["id"]):
        constraint = r["constraints"][0] if r["constraints"] else ""
        # A conflict must stay visible, including when the engine uses its reason as the constraint.
        if not constraint and r["status"] in ("outside", "blocked"):
            constraint = r["reason"]
        warning = (
            '<p class="as-constraint">' + escape(constraint) + "</p>"
            if constraint
            else ""
        )
        unknown = missing_text(r, 2)
        icon_svg = crop_icon(r.get("group_name"), r["id"])
        avatar_kind = crop_group_kind(r.get("group_name"), r["id"])
        reason_box = (
            f'<p class="as-card-reason">{escape(r["reason"])}</p>'
            if r.get("reason") and r["reason"] != constraint
            else ""
        )
        rot = previous_crop_rotation_badge(
            S.farm.current if S.farm else None, r["id"]
        )
        rot_html = ""
        if rot:
            rot_cls = (
                "as-rot-good"
                if rot["kind"] in ("legume_benefit", "good")
                else ("as-rot-caution" if rot["kind"] == "caution" else "as-rot-blocked")
            )
            rot_html = (
                f'<div><span class="as-rot-pill {rot_cls}" title="{escape(rot["detail"])}">'
                f"{escape(rot['label'])}</span></div>"
            )
        st.html(
            '<article class="as-card">'
            '<div class="as-card-top"><div>'
            + badge(r)
            + "<h2>"
            + escape(r["name"])
            + "</h2>"
            + '<p class="as-category">'
            + escape(SUPPORT.get(r["support"], r["support"]))
            + "</p>"
            + rot_html
            + "</div>"
            + f'<span class="as-crop-avatar as-avatar-{avatar_kind}" aria-hidden="true">{icon_svg}</span></div>'
            + reason_box
            + finding_list(factors(r))
            + warning
            + (
                '<p class="as-unknown"><strong>Still unknown:</strong> '
                + escape(unknown)
                + "</p>"
                if unknown
                else ""
            )
            + "</article>"
        )
        with st.container(horizontal=True):
            if st.button(
                "View details",
                key="details_" + r["id"],
                help="View details for " + r["name"],
            ):
                open_detail(r)
            compare_action(r)


def results():
    page_heading(
        "Explore your crop options",
        "Compare crops using your field conditions and available agricultural references.",
    )
    scope_line()
    render_results_summary_strip(S.cards, S.dataset, S.farm)
    if S.farm and S.farm.windows:
        render_weather_extremes_strip(S.dataset, S.farm.windows[0])
    if not S.cards:
        st.info("There isn’t enough evidence to compare crops for this season.")
        if st.button("Review my season"):
            go("season")
        if st.button("Explore climate data"):
            research("Climate history")
        return

    with st.expander("12-Month Planting Calendar Matrix (Best Sowing Windows)", expanded=False):
        render_sowing_heatmap_matrix(S.dataset, S.cards)
    if S.farm and (S.farm.ph is None or S.farm.drainage == "unknown" or S.farm.rain_fraction is None or S.farm.irrigation_mm is None):
        with st.expander("How to narrow uncertainty & resolve more crops (Value of Information)", expanded=False):
            render_voi_uncertainty_card(S.dataset, S.farm, S.cards, S.weights, S.context)

    usable = [r for r in S.cards if r["status"] in ("possible", "check")]
    if not usable:
        st.info(
            "No crop clearly fits the checks available for this field. Review the constraints before planning."
        )
    groups = {"Crops to consider": usable, "All checked crops": S.cards}
    listing = usable or S.cards
    filters = st.columns(2)
    if usable and len(usable) < len(S.cards):
        group = filters[0].selectbox("Show", list(groups), key="results_group", persist_state="session")
        listing = groups[group]
    else:
        filters[0].caption(f"{len(listing)} crops checked")
    order = filters[1].selectbox("Order", ["Assessment order", "Crop name"], key="results_order", persist_state="session")
    if order == "Crop name":
        listing = sorted(listing, key=lambda r: r["name"].casefold())
    with st.container(horizontal=True, key="result_actions"):
        if st.button(
            f"Compare selected ({len(S.comparison_ids)})",
            type="primary",
            disabled=len(S.comparison_ids) < 2,
        ):
            go("compare")
        if st.button("Edit my field"):
            go("conditions")
        if st.button("Save this farm", key="save_farm_from_results"):
            go("my_farm")
    if S.comparison_ids:
        by_id = {c["id"]: c["name"] for c in S.cards}
        chosen_names = [by_id.get(cid, cid) for cid in S.comparison_ids]
        caption("Selected for side-by-side comparison: " + ", ".join(chosen_names))
    else:
        caption(
            "Select two or three crops to compare. These checks do not predict a successful harvest."
        )
    page = min(S.card_page, (len(listing) - 1) // 4)
    start = page * 4
    with st.container(key="crop_grid"):
        for r in listing[start : start + 4]:
            card_view(r)
    if len(listing) > 4:
        with st.container(horizontal=True):
            if st.button("Previous", disabled=page == 0):
                S.card_page = page - 1
                st.rerun()
            st.caption(f"{start+1}–{min(start+4,len(listing))} of {len(listing)}")
            if st.button("Next", disabled=start + 4 >= len(listing)):
                S.card_page = page + 1
                st.rerun()
    st.divider()
    downloads(S.dataset, S.farm, S.cards, S.weights, S.context)


def remember_comparison():
    S.comparison_ids = list(S.compare_ids)


def compare():
    page_heading("Compare crops", "Review the same checks side by side.")
    scope_line()
    by = {r["id"]: r for r in S.cards}
    ids = st.multiselect(
        "Choose two or three crops",
        list(by),
        default=[i for i in S.comparison_ids if i in by],
        max_selections=3,
        key="compare_ids",
        persist_state="session",
        on_change=remember_comparison,
        format_func=lambda k: by[k]["name"],
    )
    if len(ids) < 2:
        st.info("Choose two or three crops to compare.")
    else:
        with st.container(key="compare_grid"):
            for i in ids:
                r = by[i]
                with st.container(border=True):
                    st.html(
                        '<article class="as-card">'
                        + badge(r)
                        + "<h2>"
                        + escape(r["name"])
                        + "</h2>"
                        + '<p class="as-category">'
                        + escape(SUPPORT[r["support"]])
                        + "</p>"
                        + finding_list(factors(r))
                        + "</article>"
                    )
                    if r["constraints"]:
                        st.warning(r["constraints"][0], icon=":material/info:")
                    caption("Still unknown: " + missing_text(r))
                    if st.button("View details", key="compare_" + i):
                        open_detail(r)
        render_comparison_trait_table(ids, S.cards, S.dataset, S.farm)
    if st.button("Back to results"):
        go("results")


def details():
    from .knowledge import crop_by_id, cultivar_traits, global_traits

    r = next((r for r in S.cards if r["id"] == S.detail_id), None)
    if not r:
        go("results")
    identity = crop_by_id(r["id"]) or {}
    page_heading(r["name"])
    caption(
        " · ".join(
            x
            for x in (
                identity.get("scientific_name"),
                identity.get("group_name"),
                SUPPORT[r["support"]],
            )
            if x
        )
    )
    st.html(badge(r))
    st.subheader("Why this crop is shown", anchor=False)
    st.write(r["reason"])
    from .climate_insights import previous_crop_rotation_badge

    rot = previous_crop_rotation_badge(
        S.farm.current if S.farm else None, r["id"]
    )
    if rot:
        st.caption(f"Crop succession check: {rot['detail']}")
    render_trait_visual_bars(r["id"], S.farm, S.context)
    if S.farm and S.farm.windows:
        render_stage_water_chart(r["id"], S.dataset, S.farm.windows[0])
    if r["constraints"]:
        st.subheader("Important considerations", anchor=False)
        for t in r["constraints"]:
            st.warning(t, icon=":material/info:")
    with st.container(key="dashboard_grid"):
        with st.container(border=True):
            st.subheader("What we checked", anchor=False)
            checked = r.get("assessed", [])
            if checked:
                for value in checked:
                    st.write("• " + ASSESSED.get(value, value))
            else:
                st.write("No environmental condition could be assessed.")
            st.write("**Water:** " + r["water"])
        with st.container(border=True):
            st.subheader("What remains unknown", anchor=False)
            st.write(missing_text(r) or "No additional gaps recorded by these checks.")
            caption(
                "Published references cannot establish how this crop will perform on your field."
            )
    with st.expander("6-Layer Scientific Evidence Scorecard", expanded=True):
        render_evidence_layers_card(r, S.farm, S.dataset, S.context)
    with st.expander("Scientific evidence", key="crop_evidence"):
        for t in r["details"]:
            st.write(t)
        for ref in r["sources"]:
            st.markdown(f'[{ref["title"]}]({ref["url"]})')
        traits = global_traits(r["id"])
        for t in traits:
            st.write(
                f'**{t["trait"].replace("_", " ").title()}** · {t["low"]}–{t["high"]} {t["units"]}'
            )
            caption(
                f'{t["evidence_type"]} · {t["scope"]} · retrieved {t["retrieved_on"] or "date not recorded"}'
            )
            caption(f'Cultivar: {t["cultivar"] or "not specified"} · {t["note"]}')
        cultivars = cultivar_traits(r["id"])
        for cv in cultivars:
            st.write(
                f'**Cultivar / Maturity Reference ({cv["cultivar_group"].replace("_", " ")})** · {cv["trait"].replace("_", " ")}: {cv["low"]}–{cv["high"]} {cv["units"]}'
            )
            caption(f'{cv["scope"]} · {cv["note"]}')
        if r["support"] == "regional":
            caption(
                "Regional references apply only to the confirmed Sri Lanka pilot scope. Retrieval dates are not recorded for every legacy reference."
            )
        p = S.dataset.provenance
        caption("NASA POWER · " + p["mode"])
        if p.get("retrieved_at_utc"):
            caption("Retrieved " + p["retrieved_at_utc"])
    from .screening import region_evidence

    pack = region_evidence(S.farm.country)
    with st.expander("Local growing guidance"):
        st.write(pack["scope"])
        for ref in pack["sources"]:
            st.markdown(f'[{ref["title"]}]({ref["url"]})')
    from .providers import GAEZ_CROP_ID_MAP, GAEZ_CROPS, gaez_point, gaez_polygon

    mapped = GAEZ_CROP_ID_MAP.get(r["id"])
    if mapped in GAEZ_CROPS:
        with st.expander("Compare the FAO land map", expanded=True):
            render_gaez_dual_card(S.farm.latitude, S.farm.longitude, mapped)
            if S.get("boundary"):
                poly_geo = gaez_polygon(S.boundary, mapped, "rainfed")
                if poly_geo.get("status") == "verified":
                    classes_txt = ", ".join(poly_geo.get("polygon_classes") or [str(poly_geo["value"])])
                    st.caption(
                        f"Field boundary polygon sampling ({poly_geo['sampled_points']} points): "
                        f"**{classes_txt}** · {poly_geo['resolution_note']}"
                    )
            system = st.selectbox(
                "Map scenario",
                ["rainfed", "irrigated"],
                index=None,
                placeholder="Choose a water system",
                format_func=str.title,
            )
            if system:
                geo = gaez_point(S.farm.latitude, S.farm.longitude, mapped, system)
                if geo.get("value") is not None:
                    st.write("**Mapped suitability:** " + geo["value"])
                st.caption(geo["detail"])
                st.markdown(f'[Source map]({geo["source"]})')
    from .pests import evaluate_crop_pest_context

    pest_info = evaluate_crop_pest_context(r["id"], S.dataset.frame if S.dataset else None, S.farm.windows[0] if S.farm and S.farm.windows else None)
    if pest_info.get("records"):
        with st.expander("Pest, disease, and weed context"):
            st.caption(pest_info["disclaimer"])
            for p_rec in pest_info["records"]:
                st.write(f"**{p_rec['agent_name']}** (*{p_rec.get('scientific_name') or p_rec['category']}*) · Stage: {p_rec['susceptible_stage']}")
                st.caption(f"Favorable conditions: {p_rec['favorable_condition']} · {p_rec['historical_climate_note']}")
                st.caption(f"Management context: {p_rec['cultural_notes']}")
    with st.container(horizontal=True):
        if st.button(
            "Back to comparison"
            if S.get("detail_from") == "compare"
            else "Back to results"
        ):
            go(S.get("detail_from", "results"))
        compare_action(r)
