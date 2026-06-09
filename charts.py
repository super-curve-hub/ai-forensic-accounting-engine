import pandas as pd
import numpy as np

import plotly.express as px
import plotly.graph_objects as go

import streamlit as st


# =====================================================
# Utility
# =====================================================

def score_clip(x, low=0, high=100):

    if pd.isna(x):
        return 0

    return max(
        low,
        min(
            high,
            float(x)
        )
    )


def percentile_rank(
    df,
    col,
    higher_is_better=True
):

    if col not in df.columns:
        return pd.Series(
            0,
            index=df.index
        )

    s = pd.to_numeric(
        df[col],
        errors="coerce"
    )

    if s.notna().sum() == 0:
        return pd.Series(
            0,
            index=df.index
        )

    ranks = s.rank(
        pct=True,
        ascending=higher_is_better
    )

    if not higher_is_better:
        ranks = 1 - ranks

    return (
        ranks
        .fillna(0)
        * 100
    )


# =====================================================
# Institutional Percentile Radar
# =====================================================

def radar_score_frame(compare_df):

    if compare_df.empty:
        return pd.DataFrame()

    scores = pd.DataFrame(
        index=compare_df.index
    )

    scores["ROIC"] = percentile_rank(
        compare_df,
        "ROIC",
        higher_is_better=True
    )

    scores["Gross Margin"] = percentile_rank(
        compare_df,
        "GrossMargin",
        higher_is_better=True
    )

    scores["FCF Margin"] = percentile_rank(
        compare_df,
        "FCFMargin",
        higher_is_better=True
    )

    scores["Cash Conversion"] = percentile_rank(
        compare_df,
        "CFO/NI",
        higher_is_better=True
    )

    scores["SBC Discipline"] = percentile_rank(
        compare_df,
        "SBC/Revenue",
        higher_is_better=False
    )

    temp = compare_df.copy()

    temp["CapitalAllocationRaw"] = (
        temp["ROIC-WACC"].fillna(0)
        +
        temp["BuybackYield"].fillna(0)
        -
        temp["SBC/Revenue"].fillna(0)
    )

    scores["Capital Allocation"] = percentile_rank(
        temp,
        "CapitalAllocationRaw",
        higher_is_better=True
    )

    scores["Risk Control"] = percentile_rank(
        compare_df,
        "Risk",
        higher_is_better=False
    )

    return scores


# =====================================================
# Analysis Charts
# =====================================================

def render_trend_charts(result):

    df = result["df"].copy()

    if "ROIC_TTM" in df.columns:

        tmp = df.copy()

        tmp["ROIC_pct"] = (
            tmp["ROIC_TTM"]
            * 100
        )

        fig = px.line(
            tmp,
            x="date",
            y="ROIC_pct",
            title="ROIC Trend"
        )

        fig.update_layout(
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    if "AccrualRatio" in df.columns:

        tmp = df.copy()

        tmp["Accrual_pct"] = (
            tmp["AccrualRatio"]
            * 100
        )

        fig = px.line(
            tmp,
            x="date",
            y="Accrual_pct",
            title="Accrual Trend"
        )

        fig.update_layout(
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    if "ForensicRiskScore" in df.columns:

        fig = px.bar(
            df,
            x="date",
            y="ForensicRiskScore",
            title="Forensic Risk Trend"
        )

        fig.update_layout(
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# =====================================================
# Compare Scatter
# =====================================================

def compare_scatter(compare_df):

    if compare_df.empty:
        return px.scatter()

    size_col = (
        "EconomicScore"
        if "EconomicScore" in compare_df.columns
        else "Quality"
    )

    fig = px.scatter(
        compare_df,
        x="Risk",
        y="ROIC",
        size=size_col,
        color="Grade",
        text="Ticker",
        hover_name="Ticker",
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


# =====================================================
# Institutional Quality Radar
# =====================================================

def compare_radar_v2(compare_df):

    if compare_df.empty:
        return go.Figure()

    categories = [
        "ROIC",
        "Gross Margin",
        "FCF Margin",
        "Cash Conversion",
        "SBC Discipline",
        "Capital Allocation",
        "Risk Control"
    ]

    scores = radar_score_frame(
        compare_df
    )

    fig = go.Figure()

    for idx, row in compare_df.iterrows():

        values = [
            scores.loc[idx, c]
            for c in categories
        ]

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


# =====================================================
# Economic Ranking
# =====================================================

def economic_ranking_chart(df):

    if (
        df.empty
        or
        "EconomicScore" not in df.columns
    ):
        return px.bar()

    fig = px.bar(
        df,
        x="Ticker",
        y="EconomicScore",
        color="Grade",
        title="Economic Profit Ranking"
    )

    fig.update_layout(
        height=550,
        xaxis_title="Ticker",
        yaxis_title="EconomicScore"
    )

    return fig


# =====================================================
# Regime Heatmap
# =====================================================

def regime_heatmap(df):

    if df.empty:
        return px.imshow(
            [[0]],
            title="Regime Heatmap"
        )

    heat = df.copy()

    if "ROIC" in heat.columns:
        heat["ROIC"] = heat["ROIC"] * 100

    if "ROIC-WACC" in heat.columns:
        heat["ROIC-WACC"] = heat["ROIC-WACC"] * 100

    if "Accrual" in heat.columns:
        heat["Accrual"] = heat["Accrual"] * 100

    if "CFO/NI" in heat.columns:
        heat["CFO/NI"] = heat["CFO/NI"] * 50

    if "SBC/Revenue" in heat.columns:
        heat["SBC/Revenue"] = heat["SBC/Revenue"] * 100

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
        c
        for c in cols
        if c in heat.columns
    ]

    matrix = heat[
        ["Ticker"] + available
    ].set_index(
        "Ticker"
    )

    fig = px.imshow(
        matrix,
        aspect="auto",
        text_auto=".0f",
        title="Regime Heatmap"
    )

    fig.update_layout(
        height=650
    )

    return fig


# =====================================================
# Screening Scatter
# =====================================================

def screen_scatter(screen_df):

    if screen_df.empty:
        return px.scatter()

    size_col = (
        "EconomicScore"
        if "EconomicScore" in screen_df.columns
        else "Quality"
    )

    fig = px.scatter(
        screen_df,
        x="Risk",
        y="ROIC",
        size=size_col,
        color="Regime",
        text="Ticker",
        hover_name="Ticker",
        title="Screened Candidates"
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


# =====================================================
# Portfolio Charts
# =====================================================

def portfolio_scatter(df):

    if df.empty:
        return px.scatter()

    size_col = (
        "OptWeight"
        if "OptWeight" in df.columns
        else "Weight"
    )

    fig = px.scatter(
        df,
        x="ROIC-WACC",
        y="ROIC",
        size=size_col,
        color="Grade",
        text="Ticker",
        hover_name="Ticker",
        title="Portfolio ROIC vs Economic Spread"
    )

    fig.update_traces(
        textposition="top center"
    )

    fig.update_layout(
        height=650,
        xaxis_title="ROIC-WACC",
        yaxis_title="ROIC"
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

    if (
        df.empty
        or
        "OptWeight" not in df.columns
    ):
        return px.pie()

    return px.pie(
        df,
        names="Ticker",
        values="OptWeight",
        title="Optimized Portfolio"
    )
