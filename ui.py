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
    portfolio_weights_chart,
    optimized_weights_chart,
    regime_heatmap,
    economic_ranking_chart
)

from screener import (
    DEFAULT_UNIVERSE,
    DEFAULT_WATCHLIST,
    COMPARE_PRESETS,
    run_ticker_list,
    apply_screen,
    latest_row_for_table,
    rank_companies
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
        "GrossMargin",
        "FCFMargin",
        "BuybackYieldProxy",
        "DSO",
        "InventoryDays",
        "ForensicRiskScore",
        "QualityScore",
        "Flags"
    ]

    with st.expander("Developer View"):
        st.dataframe(
            df[[c for c in cols if c in df.columns]].tail(20),
            use_container_width=True
        )


def render_analysis(
    wacc,
    wacc_pct
):

    st.subheader("Analysis")

    c1, c2 = st.columns(
        [4, 1],
        vertical_alignment="bottom"
    )

    with c1:

        ticker = st.selectbox(
            "Company",
            DEFAULT_UNIVERSE,
            index=0,
            key="analysis_ticker"
        )

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
            watch_df = rank_companies(watch_df)

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
        list(COMPARE_PRESETS.keys())
    )

    tickers = COMPARE_PRESETS[preset]

    st.caption(
        ", ".join(tickers)
    )

    if st.button(
        "Run Compare",
        key="compare_button"
    ):
        compare_df, errors = run_ticker_list(
            tickers,
            wacc
        )

        if not compare_df.empty:
            ranked = rank_companies(compare_df)

            st.markdown(
                f"### Comparing {len(ranked)} Companies"
            )

            st.plotly_chart(
                compare_scatter(ranked),
                use_container_width=True
            )

            st.plotly_chart(
                compare_radar_v2(ranked),
                use_container_width=True
            )

            st.plotly_chart(
                economic_ranking_chart(ranked),
                use_container_width=True
            )

            st.plotly_chart(
                regime_heatmap(ranked),
                use_container_width=True
            )

            with st.expander("Ranking Data"):
                st.dataframe(
                    ranked,
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

    preset = st.selectbox(
        "Screening Universe",
        list(COMPARE_PRESETS.keys())
    )

    universe = COMPARE_PRESETS[preset]

    st.caption(
        ", ".join(universe)
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        roic_min_pct = st.slider(
            "ROIC minimum (%)",
            -200.0,
            200.0,
            0.0,
            5.0
        )

    with c2:
        risk_max = st.slider(
            "Risk maximum",
            0,
            100,
            100,
            5
        )

    with c3:
        accrual_max_pct = st.slider(
            "Accrual maximum (%)",
            -100.0,
            100.0,
            100.0,
            5.0
        )

    require_cfo = st.checkbox(
        "CFO/NI > 1",
        value=False
    )

    require_spread = st.checkbox(
        "ROIC-WACC > 0",
        value=False
    )

    if st.button(
        "Run Screen",
        key="screen_button"
    ):
        raw_df, errors = run_ticker_list(
            universe,
            wacc
        )

        screen_df = apply_screen(
            raw_df,
            roic_min_pct,
            risk_max,
            accrual_max_pct,
            require_cfo_gt_1=require_cfo,
            require_positive_spread=require_spread
        )

        ranked = rank_companies(screen_df)

        st.markdown(
            f"### Results: {len(ranked)}"
        )

        if not ranked.empty:
            for _, row in ranked.iterrows():
                stock_card(row)

            st.plotly_chart(
                screen_scatter(ranked),
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
        """COHR,20
LITE,10
AVGO,20
ANET,15
MRVL,15
NVDA,20""",
        height=180
    )

    optimizer = st.selectbox(
        "Optimizer",
        [
            "Manual Weight",
            "Equal Weight",
            "Quality Weight",
            "Risk Parity",
            "Max ROIC"
        ]
    )

    if st.button(
        "Analyze Portfolio",
        key="portfolio_button"
    ):
        rows = []
        errors = []

        for line in portfolio_input.splitlines():
            try:
                ticker, weight = line.split(",")

                result = run_forensic_engine(
                    ticker.strip().upper(),
                    wacc=wacc
                )

                row = latest_row_for_table(result)
                row["Weight"] = float(weight)

                rows.append(row)

            except Exception as e:
                errors.append(
                    {
                        "Line": line,
                        "Error": str(e)
                    }
                )

        df = pd.DataFrame(rows)

        if df.empty:
            st.warning("No valid portfolio rows.")
            return

        if optimizer == "Equal Weight":
            df["OptWeight"] = 1 / len(df)

        elif optimizer == "Quality Weight":
            q = df["Quality"].fillna(0).clip(lower=0)
            df["OptWeight"] = q / q.sum()

        elif optimizer == "Risk Parity":
            inv_risk = 1 / df["Risk"].fillna(100).clip(lower=1)
            df["OptWeight"] = inv_risk / inv_risk.sum()

        elif optimizer == "Max ROIC":
            roic = df["ROIC"].fillna(0).clip(lower=0)
            df["OptWeight"] = roic / roic.sum()

        else:
            df["OptWeight"] = df["Weight"] / df["Weight"].sum()

        weights = df["OptWeight"]

        portfolio_roic = (
            df["ROIC"].fillna(0) * weights
        ).sum()

        portfolio_spread = (
            df["ROIC-WACC"].fillna(0) * weights
        ).sum()

        portfolio_risk = (
            df["Risk"].fillna(0) * weights
        ).sum()

        portfolio_quality = (
            df["Quality"].fillna(0) * weights
        ).sum()

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Portfolio ROIC",
            f"{portfolio_roic:.1%}"
        )

        c2.metric(
            "Portfolio Spread",
            f"{portfolio_spread:.1%}"
        )

        c3.metric(
            "Portfolio Risk",
            f"{portfolio_risk:.1f}"
        )

        c4.metric(
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

        st.plotly_chart(
            optimized_weights_chart(df),
            use_container_width=True
        )

        for _, row in df.iterrows():
            stock_card(row)

        if errors:
            with st.expander("Errors"):
                st.dataframe(
                    pd.DataFrame(errors),
                    use_container_width=True
                )
