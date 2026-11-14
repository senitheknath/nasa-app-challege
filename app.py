"""AgroShift Crop Finder. Start with python -m streamlit run app.py."""

import streamlit as st

from agroshift.finder_ui import (
    S,
    init,
    go,
    home,
    location,
    conditions,
    season,
    research,
)
from agroshift.finder_style import STYLE, BRAND
from agroshift.power import DataError

st.set_page_config(
    page_title="AgroShift · Crop Finder",
    page_icon=":material/eco:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
with st.container(key="app_shell"):
    init()
    st.html(STYLE)
    from agroshift.farm_ui import sync_identity, dashboard, my_farm

    try:
        store = sync_identity()
    except DataError as exc:
        st.warning(str(exc))
        if st.button("Sign in again"):
            S.clear()
            st.logout()
        st.stop()
    from agroshift.ui_components import header

    header()
    try:
        if S.page == "downloads":
            from agroshift.ui_components import page_heading, downloads

            page_heading(
                "Your farm report", "Keep a copy of this assessment and its sources."
            )
            if S.farm and S.dataset:
                downloads(S.dataset, S.farm, S.cards, S.weights, S.context)
            if st.button("Back to results"):
                go("results")
        elif S.page == "research":
            from agroshift.research_ui import render

            render()
        elif S.page == "my_farm":
            my_farm(store)
        elif S.page in ("results", "compare", "details"):
            if S.farm is None or S.dataset is None:
                st.title("Recommendations", anchor=False)
                st.info("Choose a field and growing season to find crops.")
                if st.button("Analyze my farm", type="primary"):
                    from agroshift.finder_ui import start

                    start("farm")
                st.stop()
            from agroshift.results_ui import results, compare, details

            {"results": results, "compare": compare, "details": details}[S.page]()
            if S.page == "results" and st.button("Start another farm", type="tertiary"):
                from agroshift.finder_ui import start

                start("farm")
        else:
            if S.page == "home":
                dashboard()
            else:
                with st.container(key="form_shell"):
                    {"location": location, "conditions": conditions, "season": season}[
                        S.page
                    ]()
    except DataError as exc:
        st.error(str(exc))
