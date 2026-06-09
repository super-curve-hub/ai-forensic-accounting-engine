import streamlit as st
import pandas as pd

from engine import run_forensic_engine

from cards import (
    hero_card,
    metric_cards,
    stock_card
)

from charts import (
    render_trend_charts,
    compare_scatter,
    compare_radar_v2,
    screen_scatter,
    portfolio_scatter,
    portfolio_weights_chart
)

from screener import (
    DEFAULT_UNIVERSE,
    DEFAULT_WATCHLIST,
    run_ticker_list,
    apply_screen,
    latest_row_for_table
)


def render_developer_view(result):

    df = result["df"]

    cols = [
        "date",
        "Revenue_TTM",
        "NOPAT_TTM",
        "ROIC_TTM",
        "ROIC_WACC_Spread",
        "EconomicEarnings_TTM",
        "AccrualRatio",
        "CFO_to_NI",
        "FCF_to_NI",
        "SBC_to_Revenue",
        "DSO",
        "InventoryDays",
        "ForensicRiskScore",
        "QualityScore",
        "Flags"
    ]

    with st.expander("Developer View"):

        st.dataframe(
            df[
                [
                    c
                    for c in cols
                    if c in df.columns
                ]
            ].tail(20),
            use_container_width=True
        )


def render_analysis(
    wacc,
    wacc_pct
):

    st.subheader("Analysis")

    c1, c2 = st.columns([3, 1])

    with c1:

        ticker = st.text_input(
            "Ticker",
            "NVDA",
            key="analysis_ticker"
        ).upper().strip()

    with c2:

        run = st.button(
            "Analyze",
            use_container_width=True
        )

    if run:

        try:

            with st.spinner(
                f"Analyzing {ticker}..."
            ):

                result = run_forensic_engine(
                    ticker,
                    wacc=wacc
                )

            latest = result["latest"]

            hero_card(
                latest,
                wacc_pct
            )

            metric_cards(
                latest
            )

            render_trend_charts(
                result
            )

            render_developer_view(
                result
            )

        except Exception as e:

            st.error(
                "Analysis failed."
            )

            st.exception(e)


def render_watchlist(wacc):

    st.subheader("Watchlist")

    selected = st.multiselect(
        "Tickers",
        DEFAULT_UNIVERSE,
        default=DEFAULT_WATCHLIST
    )

    if st.button(
        "Run Watchlist",
        key="watchlist_button"
    ):

        watch_df, errors = run_ticker_list(
            selected,
            wacc
        )

        if not watch_df.empty:

            watch_df = watch_df.sort_values(
                "Quality",
                ascending=False
            )

            st.markdown(
                f"### {len(watch_df)} Companies"
            )

            for _, row in watch_df.iterrows():

                stock_card(row)

        if not errors.empty:

            with st.expander("Errors"):

                st.dataframe(
                    errors,
                    use_container_width=True
                )


def render_compare(wacc):

    st.subheader("Compare")

    preset = st.selectbox(
        "Compare Preset",
        [
            "Photonics",
            "AI Infrastructure",
            "Magnificent 7"
        ]
    )

    if preset == "Photonics":

        default_compare = [
            "COHR",
            "LITE",
            "AVGO",
            "ANET",
            "MRVL",
            "NVDA"
        ]

    elif preset == "AI Infrastructure":

        default_compare = [
            "NVDA",
            "AVGO",
            "AMD",
            "MU",
            "ANET",
            "MRVL"
        ]

    else:

        default_compare = [
            "AAPL",
            "MSFT",
            "AMZN",
            "META",
            "GOOG",
            "NVDA",
            "TSLA"
        ]

    st.caption(
        ", ".join(default_compare)
    )

    if st.button(
        "Run Compare",
        key="compare_button"
    ):

        compare_df, errors = run_ticker_list(
            default_compare,
            wacc
        )

        if not compare_df.empty:

            st.markdown(
                f"### Comparing {len(compare_df)} Companies"
            )

            st.plotly_chart(
                compare_scatter(compare_df),
                use_container_width=True
            )

            st.plotly_chart(
                compare_radar_v2(compare_df),
                use_container_width=True
            )

            st.dataframe(
                compare_df,
                use_container_width=True
            )

        if not errors.empty:

            with st.expander("Errors"):

                st.dataframe(
                    errors,
                    use_container_width=True
                )
def render_screening(wacc):

    st.subheader("Screening")

    universe_text = st.text_area(
        "Universe",
        ", ".join(DEFAULT_UNIVERSE),
        height=100
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        roic_min_pct = st.slider(
            "ROIC minimum (%)",
            -200.0,
            200.0,
            20.0,
            5.0
        )

    with c2:

        risk_max = st.slider(
            "Risk maximum",
            0,
            100,
            40,
            5
        )

    with c3:

        accrual_max_pct = st.slider(
            "Accrual maximum (%)",
            -100.0,
            100.0,
            5.0,
            5.0
        )

    if st.button(
        "Run Screen",
        key="screen_button"
    ):

        universe = [
            x.strip().upper()
            for x in universe_text
            .replace("\n", ",")
            .split(",")
            if x.strip()
        ]

        raw_df, errors = run_ticker_list(
            universe,
            wacc
        )

        screen_df = apply_screen(
            raw_df,
            roic_min_pct,
            risk_max,
            accrual_max_pct
        )

        st.markdown(
            f"### Results: {len(screen_df)}"
        )

        if not screen_df.empty:

            for _, row in screen_df.iterrows():

                stock_card(row)

            st.plotly_chart(
                screen_scatter(screen_df),
                use_container_width=True
            )

        if not errors.empty:

            with st.expander("Errors"):

                st.dataframe(
                    errors,
                    use_container_width=True
                )


def render_portfolio(wacc):

    st.subheader("Portfolio")

    portfolio_input = st.text_area(
        "Ticker,Weight",
        """NVDA,30
AVGO,20
META,15
AAPL,15
MSFT,20""",
        height=180
    )

    if st.button(
        "Analyze Portfolio",
        key="portfolio_button"
    ):

        rows = []

        for line in portfolio_input.splitlines():

            try:

                ticker, weight = line.split(",")

                result = run_forensic_engine(
                    ticker.strip().upper(),
                    wacc=wacc
                )

                row = latest_row_for_table(
                    result
                )

                row["Weight"] = float(
                    weight
                )

                rows.append(
                    row
                )

            except Exception:
                pass

        df = pd.DataFrame(rows)

        if df.empty:

            st.warning(
                "No valid portfolio rows."
            )

            return

        weights = (
            df["Weight"]
            /
            df["Weight"].sum()
        )

        portfolio_roic = (
            df["ROIC"].fillna(0)
            * weights
        ).sum()

        portfolio_risk = (
            df["Risk"].fillna(0)
            * weights
        ).sum()

        portfolio_quality = (
            df["Quality"].fillna(0)
            * weights
        ).sum()

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Portfolio ROIC",
                f"{portfolio_roic:.1%}"
            )

        with c2:
            st.metric(
                "Portfolio Risk",
                f"{portfolio_risk:.1f}"
            )

        with c3:
            st.metric(
                "Portfolio Quality",
                f"{portfolio_quality:.0f}"
            )

        st.plotly_chart(
            portfolio_scatter(df),
            use_container_width=True
        )

        st.plotly_chart(
            portfolio_weights_chart(df),
            use_container_width=True
        )

        for _, row in df.iterrows():

            stock_card(row)
