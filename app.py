import streamlit as st

from cards import inject_card_css, page_title
from ui import render_analysis, render_watchlist, render_compare, render_screening

st.set_page_config(
    page_title="AI Forensic Accounting Engine v3",
    layout="wide"
)

inject_card_css()
page_title()

with st.sidebar:
    st.subheader("Settings")
    wacc_pct = st.number_input(
        "WACC (%)",
        min_value=0.0,
        max_value=30.0,
        value=10.0,
        step=0.5
    )
    wacc = wacc_pct / 100
    st.caption("Example: 14% = input 14.0")

tab1, tab2, tab3, tab4 = st.tabs([
    "Analysis",
    "Watchlist",
    "Compare",
    "Screening"
])

with tab1:
    render_analysis(wacc, wacc_pct)

with tab2:
    render_watchlist(wacc)

with tab3:
    render_compare(wacc)

with tab4:
    render_screening(wacc)

st.caption("v3 Full Modular Edition: card-centered UX + SEC/XBRL engine + Watchlist + Compare + Screening.")
