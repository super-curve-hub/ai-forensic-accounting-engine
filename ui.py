import streamlit as st
import pandas as pd

from engine import run_forensic_engine
from cards import hero_card, metric_cards, stock_card
from charts import render_trend_charts, compare_bar, compare_radar, screen_scatter
from screener import DEFAULT_UNIVERSE, DEFAULT_WATCHLIST, run_ticker_list, apply_screen

def render_developer_view(result):
    df = result["df"]
    cols = [
        "date", "Revenue_TTM", "COGS_TTM", "NOPAT_TTM", "ROIC_TTM",
        "ROIC_WACC_Spread", "EconomicEarnings_TTM",
        "AccrualRatio", "CFO_to_NI", "FCF_to_NI",
        "SBC_to_Revenue", "DSO", "InventoryDays",
        "ForensicRiskScore", "QualityScore", "Flags"
    ]

    with st.expander("Developer view: raw financial data"):
        st.dataframe(df[[c for c in cols if c in df.columns]].tail(20), use_container_width=True)

    with st.expander("Developer view: resolved XBRL tags"):
        st.dataframe(
            pd.DataFrame([{"Metric": k, "ResolvedTag": v} for k, v in result["used_tags"].items()]),
            use_container_width=True
        )

def render_analysis(wacc, wacc_pct):
    st.subheader("Analysis")

    c1, c2 = st.columns([3, 1])
    with c1:
        ticker = st.text_input("Ticker", "NVDA", key="analysis_ticker").upper().strip()
    with c2:
        run = st.button("Analyze", use_container_width=True)

    if run:
        try:
            with st.spinner(f"Analyzing {ticker}..."):
                result = run_forensic_engine(ticker, wacc=wacc)

            latest = result["latest"]
            hero_card(latest, wacc_pct)
            metric_cards(latest)
            render_trend_charts(result)
            render_developer_view(result)

        except Exception as e:
            st.error("Analysis failed.")
            st.exception(e)

def render_watchlist(wacc):
    st.subheader("Watchlist")

    selected = st.multiselect(
        "Tickers",
        DEFAULT_UNIVERSE,
        default=DEFAULT_WATCHLIST
    )

    if st.button("Run Watchlist"):
        rows = []
        errors = []
        progress = st.progress(0)

        for i, ticker in enumerate(selected):
            try:
                with st.spinner(f"Analyzing {ticker}..."):
                    result = run_forensic_engine(ticker, wacc=wacc)
                    from screener import latest_row_for_table
                    rows.append(latest_row_for_table(result))
            except Exception as e:
                errors.append({"Ticker": ticker, "Error": str(e)})

            progress.progress((i + 1) / max(len(selected), 1))

        watch_df = pd.DataFrame(rows)

        if not watch_df.empty:
            for _, row in watch_df.iterrows():
                stock_card(row)

        if errors:
            with st.expander("Errors"):
                st.dataframe(pd.DataFrame(errors), use_container_width=True)

def render_compare(wacc):
    st.subheader("Compare")

    compare_input = st.text_input(
        "Tickers separated by comma",
        "NVDA, AVGO, AMD",
        key="compare_input"
    )

    if st.button("Run Compare"):
        tickers = [
            x.strip().upper()
            for x in compare_input.split(",")
            if x.strip()
        ]

        compare_df, errors = run_ticker_list(tickers, wacc)

        if not compare_df.empty:
            for _, row in compare_df.iterrows():
                stock_card(row)

            st.plotly_chart(compare_bar(compare_df), use_container_width=True)
            st.plotly_chart(compare_radar(compare_df), use_container_width=True)

        if not errors.empty:
            with st.expander("Errors"):
                st.dataframe(errors, use_container_width=True)

def render_screening(wacc):
    st.subheader("Screening")

    preset = st.selectbox(
        "Preset",
        ["Custom", "Quality Compounder", "AI Infrastructure", "High SBC Risk"]
    )

    default_universe = DEFAULT_UNIVERSE

    if preset == "AI Infrastructure":
        default_universe = ["NVDA", "AVGO", "AMD", "MU", "MRVL", "ANET"]
    elif preset == "High SBC Risk":
        default_universe = ["PLTR", "SNOW", "AUR", "CRWD"]

    universe_text = st.text_area(
        "Universe tickers",
        ", ".join(default_universe),
        height=100
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        roic_min_pct = st.slider("ROIC minimum (%)", -200.0, 200.0, 20.0, 5.0)

    with c2:
        risk_max = st.slider("Risk maximum", 0, 100, 40, 5)

    with c3:
        accrual_max_pct = st.slider("Accrual maximum (%)", -100.0, 100.0, 5.0, 5.0)

    require_cfo = False

    if preset == "Quality Compounder":
        roic_min_pct = 20.0
        risk_max = 20
        accrual_max_pct = 0.0
        require_cfo = True
        st.info("Quality Compounder preset: ROIC > 20%, Risk < 20, Accrual < 0, CFO/NI > 1")

    if st.button("Run Screen"):
        universe = [
            x.strip().upper()
            for x in universe_text.replace("\n", ",").split(",")
            if x.strip()
        ]

        rows = []
        errors = []
        progress = st.progress(0)

        from screener import latest_row_for_table

        for i, ticker in enumerate(universe):
            try:
                with st.spinner(f"Screening {ticker}..."):
                    result = run_forensic_engine(ticker, wacc=wacc)
                    rows.append(latest_row_for_table(result))
            except Exception as e:
                errors.append({"Ticker": ticker, "Error": str(e)})

            progress.progress((i + 1) / max(len(universe), 1))

        raw_df = pd.DataFrame(rows)
        screen_df = apply_screen(raw_df, roic_min_pct, risk_max, accrual_max_pct, require_cfo)

        st.markdown(f"### Results: {len(screen_df)} hits")

        if not screen_df.empty:
            for _, row in screen_df.iterrows():
                stock_card(row)

            st.plotly_chart(screen_scatter(screen_df), use_container_width=True)

        with st.expander("All screened tickers"):
            st.dataframe(raw_df, use_container_width=True)

        if errors:
            with st.expander("Errors"):
                st.dataframe(pd.DataFrame(errors), use_container_width=True)
