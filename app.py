import streamlit as st

from cards import (
    inject_card_css,
    page_title
)

from ui import (
    render_analysis,
    render_watchlist,
    render_compare,
    render_screening,
    render_portfolio
)

# ==========================================================
# Page Config
# ==========================================================

st.set_page_config(
    page_title="AI Forensic Accounting Engine v4",
    layout="wide"
)

inject_card_css()

page_title()

# ==========================================================
# Sidebar
# ==========================================================

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

    st.caption(
        "Example: 14% = input 14.0"
    )

# ==========================================================
# Tabs
# ==========================================================

tab_analysis, \
tab_watchlist, \
tab_compare, \
tab_screening, \
tab_portfolio = st.tabs([
    "Analysis",
    "Watchlist",
    "Compare",
    "Screening",
    "Portfolio"
])

# ==========================================================
# Analysis
# ==========================================================

with tab_analysis:

    render_analysis(
        wacc=wacc,
        wacc_pct=wacc_pct
    )

# ==========================================================
# Watchlist
# ==========================================================

with tab_watchlist:

    render_watchlist(
        wacc=wacc
    )

# ==========================================================
# Compare
# ==========================================================

with tab_compare:

    render_compare(
        wacc=wacc
    )

# ==========================================================
# Screening
# ==========================================================

with tab_screening:

    render_screening(
        wacc=wacc
    )

# ==========================================================
# Portfolio
# ==========================================================

with tab_portfolio:

    render_portfolio(
        wacc=wacc
    )

# ==========================================================
# Footer
# ==========================================================

st.caption(
    "AI Forensic Accounting Engine v4 | "
    "Card-Centered UX | "
    "Analysis + Watchlist + Compare + Screening + Portfolio"
)
