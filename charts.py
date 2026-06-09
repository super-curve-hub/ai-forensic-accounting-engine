import pandas as pd

import plotly.express as px

import streamlit as st


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
# Economic Profit Ranking
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
# ROIC vs Risk Scatter
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
        heat["ROIC"] = (
            heat["ROIC"]
            * 100
        )

    if "ROIC-WACC" in heat.columns:
        heat["ROIC-WACC"] = (
            heat["ROIC-WACC"]
            * 100
        )

    if "Accrual" in heat.columns:
        heat["Accrual"] = (
            heat["Accrual"]
            * 100
        )

    if "CFO/NI" in heat.columns:
        heat["CFO/NI"] = (
            heat["CFO/NI"]
            * 50
        )

    if "SBC/Revenue" in heat.columns:
        heat["SBC/Revenue"] = (
            heat["SBC/Revenue"]
            * 100
        )

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
# Portfolio Optimizer Charts
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

    fig = px.pie(
        df,
        names="Ticker",
        values="Weight",
        title="Portfolio Allocation"
    )

    fig.update_layout(
        height=600
    )

    return fig


def optimized_weights_chart(df):

    if (
        df.empty
        or
        "OptWeight" not in df.columns
    ):
        return px.pie()

    fig = px.pie(
        df,
        names="Ticker",
        values="OptWeight",
        title="Optimized Portfolio"
    )

    fig.update_layout(
        height=600
    )

    return fig
