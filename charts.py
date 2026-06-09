import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def score_clip(x, low=0, high=100):
    if pd.isna(x):
        return 0
    return max(low, min(high, float(x)))


def quality_scores(row):
    roic = row.get("ROIC", np.nan)
    accrual = row.get("Accrual", np.nan)
    cfo = row.get("CFO/NI", np.nan)
    sbc = row.get("SBC/Revenue", np.nan)
    risk = row.get("Risk", np.nan)
    gross_margin = row.get("GrossMargin", np.nan)
    fcf_margin = row.get("FCFMargin", np.nan)
    buyback = row.get("BuybackYield", np.nan)

    return {
        "ROIC": score_clip(roic * 100) if pd.notna(roic) else 0,
        "Gross Margin": score_clip(gross_margin * 100) if pd.notna(gross_margin) else 0,
        "FCF Margin": score_clip(fcf_margin * 100) if pd.notna(fcf_margin) else 0,
        "Cash Conversion": score_clip((cfo / 1.5) * 100) if pd.notna(cfo) else 0,
        "Accrual": score_clip(100 - abs(accrual) * 500) if pd.notna(accrual) else 0,
        "SBC": score_clip(100 - sbc * 500) if pd.notna(sbc) else 0,
        "Buyback Yield": score_clip(buyback * 100) if pd.notna(buyback) else 0,
        "Risk Control": score_clip(100 - risk) if pd.notna(risk) else 0,
    }


def render_trend_charts(result):
    df = result["df"].copy()

    if "ROIC_TTM" in df.columns:
        tmp = df.copy()
        tmp["ROIC_pct"] = tmp["ROIC_TTM"] * 100

        st.plotly_chart(
            px.line(
                tmp,
                x="date",
                y="ROIC_pct",
                title="ROIC Trend"
            ),
            use_container_width=True
        )

    if "AccrualRatio" in df.columns:
        tmp = df.copy()
        tmp["Accrual_pct"] = tmp["AccrualRatio"] * 100

        st.plotly_chart(
            px.line(
                tmp,
                x="date",
                y="Accrual_pct",
                title="Accrual Trend"
            ),
            use_container_width=True
        )

    if "ForensicRiskScore" in df.columns:
        st.plotly_chart(
            px.bar(
                df,
                x="date",
                y="ForensicRiskScore",
                title="Forensic Risk Trend"
            ),
            use_container_width=True
        )


def compare_scatter(compare_df):
    if compare_df.empty:
        return px.scatter()

    fig = px.scatter(
        compare_df,
        x="Risk",
        y="ROIC",
        size="Quality",
        color="Grade",
        hover_name="Ticker",
        text="Ticker",
        title="ROIC vs Forensic Risk"
    )

    fig.update_traces(
        textposition="top center"
    )

    fig.update_layout(
        height=650,
        xaxis_title="Forensic Risk",
        yaxis_title="ROIC"
    )

    return fig


def compare_radar_v2(compare_df):
    categories = [
        "ROIC",
        "Gross Margin",
        "FCF Margin",
        "Cash Conversion",
        "Accrual",
        "SBC",
        "Buyback Yield",
        "Risk Control"
    ]

    fig = go.Figure()

    for _, row in compare_df.iterrows():
        scores = quality_scores(row)
        values = [scores[c] for c in categories]

        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=row["Ticker"]
            )
        )

    fig.update_layout(
        title="Institutional Quality Radar",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        height=850
    )

    return fig


def regime_heatmap(df):
    if df.empty:
        return px.imshow([[0]], title="Regime Heatmap")

    cols = [
        "ROIC",
        "ROIC-WACC",
        "Accrual",
        "CFO/NI",
        "SBC/Revenue",
        "Risk",
        "Quality"
    ]

    available = [
        c for c in cols
        if c in df.columns
    ]

    matrix = df[
        ["Ticker"] + available
    ].set_index("Ticker")

    fig = px.imshow(
        matrix,
        aspect="auto",
        title="Regime Heatmap",
        text_auto=".2f"
    )

    fig.update_layout(
        height=650
    )

    return fig


def economic_ranking_chart(df):
    if df.empty or "EconomicScore" not in df.columns:
        return px.bar()

    fig = px.bar(
        df,
        x="Ticker",
        y="EconomicScore",
        color="Grade",
        title="Economic Profit Ranking"
    )

    fig.update_layout(
        height=550
    )

    return fig


def screen_scatter(screen_df):
    if screen_df.empty:
        return px.scatter()

    fig = px.scatter(
        screen_df,
        x="Risk",
        y="ROIC",
        color="Regime",
        size="Quality",
        hover_name="Ticker",
        text="Ticker",
        title="Screened Candidates"
    )

    fig.update_traces(
        textposition="top center"
    )

    return fig


def portfolio_scatter(df):
    if df.empty:
        return px.scatter()

    fig = px.scatter(
        df,
        x="ROIC-WACC",
        y="ROIC",
        size="Weight",
        color="Grade",
        text="Ticker",
        hover_name="Ticker",
        title="Portfolio ROIC vs Economic Spread"
    )

    fig.update_traces(
        textposition="top center"
    )

    return fig


def portfolio_weights_chart(df):
    if df.empty:
        return px.pie()

    return px.pie(
        df,
        names="Ticker",
        values="Weight",
        title="Portfolio Allocation"
    )


def optimized_weights_chart(df):
    if df.empty or "OptWeight" not in df.columns:
        return px.pie()

    return px.pie(
        df,
        names="Ticker",
        values="OptWeight",
        title="Optimized Portfolio"
    )
