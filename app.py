import streamlit as st
from ui import render_analysis, render_watchlist, render_compare, render_screening

st.set_page_config(page_title="AI Forensic Accounting Engine v3", layout="wide")

tab1, tab2, tab3, tab4 = st.tabs(["Analysis","Watchlist","Compare","Screening"])

with tab1:
    render_analysis()

with tab2:
    render_watchlist()

with tab3:
    render_compare()

with tab4:
    render_screening()
