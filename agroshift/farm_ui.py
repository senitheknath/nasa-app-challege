"""Four-destination farmer workspace; private persistence is optional."""

from dataclasses import asdict
import json
import os

import streamlit as st
from .finder_ui import S, go, start, home, finish
from .farm_records import farm_from_dict, profile, read_profile, new_session_record
from .finder_report import make_record, readable
from .power import DataError


def configured():
    if not (
        os.getenv("AGROSHIFT_PRIVATE_DATABASE_URL")
        and os.getenv("AGROSHIFT_OIDC_ISSUER")
    ):
        return False
    try:
        auth = st.secrets["auth"]
        return all(
            auth.get(k)
            for k in (
                "redirect_uri",
                "cookie_secret",
                "client_id",
                "client_secret",
                "server_metadata_url",
            )
        )
    except (FileNotFoundError, KeyError):
        return False


def signed_store():
    if not configured():
        return None
    from .private_store import PrivateStore, owner_from_claims

    claims = st.user.to_dict()
    if not claims.get("is_logged_in"):
        return None
    owner = owner_from_claims(claims, os.environ["AGROSHIFT_OIDC_ISSUER"])
    return PrivateStore(os.environ["AGROSHIFT_PRIVATE_DATABASE_URL"], owner)


def sync_identity():
    # A different sign-in must never inherit widgets or farms from the prior account.
    store = signed_store()
    owner = store.owner if store else "session"
    if S.get("storage_owner", owner) != owner:
        S.clear()
        from .finder_ui import init

        init()
    S.storage_owner = owner
    return store


def records(store):
    rows = store.farms() if store else list(S.session_farms.values())
    return {str(r["id"]): dict(r, id=str(r["id"])) for r in rows}


def active_record(store):
    return records(store).get(S.active_farm_id)


def assessment():
    return make_record(S.dataset, S.farm, S.cards, S.weights, S.context)


def activate(value, identifier=None, revision=0):
    from .locations import load_history
    from .farm_context import location_context

    farm = farm_from_dict(value["farm"])
    # Prepare everything first; failed climate retrieval leaves the old field intact.
    with st.spinner("Loading this farm…"):
        dataset = load_history(farm.latitude, farm.longitude)
        context = location_context(
            farm.country,
            farm.latitude,
            farm.longitude,
            offline="demonstration" in farm.input_origin,
        )
    from .ui_state import clear_wizard

    clear_wizard()
    S.dataset = dataset
    S.farm = farm
    S.point = (farm.country, farm.latitude, farm.longitude, value["location_label"])
    S.context = context
    S.demo_active = "demonstration" in farm.input_origin
    S.target = "farm"
    S.active_farm_id = identifier
    S.active_revision = revision
    S.farm_name = value["name"]
    S.boundary = value["boundary"]
    S.draft = {
        k: v
        for k, v in asdict(farm).items()
        if k not in {"latitude", "longitude", "country", "input_origin", "windows"}
    }
    S.draft["windows"] = farm.windows
    finish(farm)


def save(store, name):
    value = profile(name, S.farm, S.point[3], S.boundary)
    if store:
        row = store.save_farm(value, S.active_farm_id, S.active_revision)
        row["id"] = str(row["id"])
    else:
        old = S.session_farms.get(S.active_farm_id)
        if old and old["revision"] != S.active_revision:
            raise DataError("Reload this farm before saving.")
        row = new_session_record(value, S.active_farm_id, S.active_revision)
        S.session_farms[row["id"]] = row
    S.active_farm_id = row["id"]
    S.active_revision = row["revision"]
    S.farm_name = name.strip()
    S["wf_farm_name"] = S.farm_name
    record = assessment()
    if store:
        try:
            store.save_analysis(row["id"], record)
        except DataError as exc:
            raise DataError(
                "The farm was saved, but its assessment could not be saved. Try Save farm again."
            ) from exc
    else:
        history = S.session_history.setdefault(row["id"], [])
        # Re-saving the same result should not multiply identical history entries.
        signature = lambda r: json.dumps(
            {k: v for k, v in r.items() if k != "generated_at"}, sort_keys=True
        )
        if not history or signature(history[0]["report"]) != signature(record):
            history.insert(
                0,
                dict(
                    id=str(len(history) + 1),
                    created_at=record["generated_at"],
                    report=record,
                ),
            )
    return row


def dashboard():
    from .ui_components import (
        page_heading,
        context_bar,
        caption,
        render_site_intelligence_banner,
        render_calendar_strip,
    )

    if S.farm is None:
        home()
        return
    page_heading("Dashboard", "Your field, environmental intelligence, and latest assessment.")
    render_site_intelligence_banner(S.dataset, S.context, S.point)
    render_calendar_strip(S.dataset, S.farm.windows[0] if S.farm.windows else None)
    with st.container(key="dashboard_grid"):
        with st.container(border=True):
            st.subheader(S.farm_name or "Your selected field", anchor=False)
            context_bar([("Location", S.point[3]), ("Season", S.farm.windows[0].label)])
            caption("Example profile" if S.demo_active else "Active farm")
            if st.button("View or edit farm"):
                go("my_farm")
        with st.container(border=True):
            st.subheader("Latest assessment", anchor=False)
            st.write(f"**{len(S.cards)} crops checked**")
            p = S.dataset.provenance
            caption(
                f"NASA weather history · {p['request']['start'][:4]}–{p['request']['end'][:4]}"
            )
            missing = []
            if S.farm.ph is None:
                missing.append("measured soil pH")
            if S.farm.drainage == "unknown":
                missing.append("drainage")
            if S.farm.irrigation_mm is None or S.farm.rain_fraction is None:
                missing.append("seasonal water amounts")
            caption(
                "Still unknown: " + ", ".join(missing)
                if missing
                else "Review crop details for remaining limitations."
            )
            if S.get("assessed_at"):
                caption(
                    "Last checked · " + S.assessed_at[:16].replace("T", " ") + " UTC"
                )
            if st.button("View results", type="primary"):
                go("results")
    st.subheader("Quick actions", anchor=False)
    with st.container(horizontal=True):
        if st.button("Analyze another farm"):
            start("farm")
        if st.button("Browse crops"):
            from .finder_ui import research

            research("Crop catalogue")
        if st.button("Explore climate"):
            from .finder_ui import research

            research("Climate history")
    if S.setup_page and st.button("Continue farm setup"):
        go(S.setup_page)


def capability_view():
    from .farm_context import capabilities

    for code, item in capabilities(S.farm, S.dataset, S.cards).items():
        st.write(
            f"**{code} · {item['label']}** — {'Available' if item['available'] else 'Not available'}"
        )
        st.caption(item["scope"])


def boundary_editor():
    with st.expander("Field boundary (optional)", key="boundary_panel"):
        st.caption(
            "A boundary identifies your field. Weather and soil estimates still use the selected point."
        )
        if st.checkbox("Draw or edit on a map", key="draw_boundary"):
            import folium
            from folium.plugins import Draw
            from streamlit_folium import st_folium
            from .ui_components import satellite_map

            m = satellite_map(
                S.farm.latitude,
                S.farm.longitude,
                zoom=15,
                label="Selected field point",
                boundary=S.boundary,
            )
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
            drawn = st_folium(
                m,
                height=340,
                use_container_width=True,
                key="boundary_" + str(S.active_farm_id),
                returned_objects=["all_drawings"],
            )
            if drawn and drawn.get("all_drawings"):
                candidate = drawn["all_drawings"][-1].get("geometry")
                from .farm_records import boundary_polygon, polygon_area_hectares

                cand_ha = polygon_area_hectares(candidate)
                if cand_ha is not None:
                    st.caption(
                        f"Drawn polygon area: **{cand_ha:.2f} ha** ({cand_ha * 2.47105:.2f} acres)"
                    )
                if st.button("Use drawn boundary"):
                    S.boundary = boundary_polygon(candidate, S.farm)
                    st.success("Boundary ready. Save farm to keep it.")
        if S.boundary:
            from .farm_records import polygon_area_hectares

            b_ha = polygon_area_hectares(S.boundary)
            area_note = f" ({b_ha:.2f} ha / {b_ha * 2.47105:.2f} acres)" if b_ha is not None else ""
            st.caption(f"A field boundary is attached{area_note}.")
            if st.button("Remove boundary"):
                S.boundary = None
                st.rerun()


def my_farm(store):
    if S.pop("close_boundary_after_save", False):
        S["draw_boundary"] = False
    from .ui_components import page_heading, empty_state, caption, context_bar
    from html import escape

    page_heading("My Farm", "Manage your fields and growing conditions.")
    if store:
        caption("Private account storage")
    else:
        caption("Saved for this session. Export a farm to keep it across visits.")
    if st.button("Add a farm", type="primary"):
        start("farm")
    available = records(store)
    if available:
        ids = list(available)
        page = (
            st.number_input(
                "Farm list page",
                min_value=1,
                max_value=max(1, (len(ids) + 3) // 4),
                value=1,
                step=1,
            )
            if len(ids) > 4
            else 1
        )
        with st.container(key="farm_grid"):
            for key in ids[(page - 1) * 4 : page * 4]:
                row = available[key]
                p = row["profile"]
                farm = farm_from_dict(p["farm"])
                with st.container(border=True):
                    st.html(
                        '<h2 class="as-farm-title">'
                        + escape(p["name"])
                        + '</h2><p class="as-farm-meta">'
                        + escape(p["location_label"])
                        + "</p>"
                    )
                    caption(farm.windows[0].label)
                    if row.get("updated_at"):
                        caption("Updated " + str(row["updated_at"])[:10])
                    if key == S.active_farm_id:
                        caption("Selected farm")
                    if st.button(
                        "Open farm", key="open_farm_" + key, help="Open " + p["name"]
                    ):
                        activate(p, key, row["revision"])
    elif S.farm is None:
        empty_state(
            "Your agricultural workspace starts here.",
            "Add a farm to explore crop options.",
        )
    if S.farm is not None:
        st.subheader("Selected field", anchor=False)
        context_bar([("Location", S.point[3]), ("Season", S.farm.windows[0].label)])
        name = st.text_input(
            "Farm name",
            value=S.farm_name or "",
            max_chars=80,
            key="farm_name_" + str(S.active_farm_id),
            persist_state="session",
        )
        boundary_editor()
        with st.container(horizontal=True):
            if st.button("Save farm", type="primary"):
                save(store, name)
                S.farm_flash = "Farm and assessment saved."
                S.close_boundary_after_save = True
                st.rerun()
            if st.button("Edit field details"):
                go("conditions")
        if S.pop("farm_flash", None):
            st.success("Farm and assessment saved.")
        if name.strip():
            st.download_button(
                "Export farm",
                json.dumps(profile(name, S.farm, S.point[3], S.boundary), indent=2),
                "agroshift-farm.json",
                "application/json",
                on_click="ignore",
            )
        if S.active_farm_id:
            with st.expander("Assessment history", key="history_panel"):
                index = st.number_input(
                    "History page",
                    min_value=1,
                    value=1,
                    step=1,
                    key="history_page_" + S.active_farm_id,
                )
                old = (
                    store.history(S.active_farm_id, (index - 1) * 10)
                    if store
                    else S.session_history.get(S.active_farm_id, [])[
                        (index - 1) * 10 : index * 10
                    ]
                )
                if not old:
                    st.caption("No saved assessments on this page.")
                for item in old:
                    record = item["report"]
                    st.write(str(item["created_at"])[:16].replace("T", " "))
                    st.caption(
                        f"{len(record['options'])} crops · saved inputs and reference versions"
                    )
                    st.download_button(
                        "Download saved report",
                        readable(record),
                        "agroshift-saved-report.html",
                        "text/html",
                        key="history_" + str(item["id"]),
                        on_click="ignore",
                    )
    with st.expander("Import a farm", key="import_panel"):
        upload = st.file_uploader(
            "AgroShift farm file", type=["json"], max_upload_size=1, key="farm_import"
        )
        if upload and st.button("Open imported farm"):
            activate(read_profile(upload.getvalue()))
    if configured():
        with st.expander("Account"):
            if store:
                display = st.text_input(
                    "Your name (optional)", value=store.account(), max_chars=80
                )
                if st.button("Save name"):
                    store.account(display)
                    st.success("Name saved.")
                if st.button("Sign out"):
                    S.clear()
                    st.logout()
            else:
                if st.button("Sign in to save across visits"):
                    try:
                        st.login()
                    except Exception:
                        st.error(
                            "Sign-in is unavailable. You can still export this farm."
                        )
