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
            tmp["ROIC_TTM"] * 100
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
            tmp["AccrualRatio"] * 100
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

    plot_df = compare_df.copy()

    if "EconomicScore" in plot_df.columns:

        plot_df["BubbleSize"] = (
            plot_df["EconomicScore"]
            .fillna(1)
            .clip(lower=1)
            ** 0.5
        )

    else:

        plot_df["BubbleSize"] = (
            plot_df["Quality"]
            .fillna(1)
            .clip(lower=1)
            ** 0.5
        )

    fig = px.scatter(
        plot_df,
        x="Risk",
        y="EconomicScore",
        size="BubbleSize",
        size_max=50,
        color="EconomicScore",
        color_continuous_scale="RdYlGn",
        hover_name="Ticker",
        text="Ticker",
        hover_data={
            "ROIC": ":.1%",
            "ROIC-WACC": ":.1%",
            "Risk": ":.1f",
            "EconomicScore": ":.1f",
            "Quality": ":.0f"
        },
        title="Economic Profit vs Risk"
    )

    fig.update_traces(
        textposition="top center",
        textfont_size=11
    )

    fig.update_layout(
        height=750,
        xaxis_title="Forensic Risk",
        yaxis_title="Economic Score",
        coloraxis_colorbar_title="Economic Score",
        showlegend=False,
        hovermode="closest"
    )

    fig.update_xaxes(
        zeroline=True,
        zerolinewidth=1
    )

    fig.update_yaxes(
        zeroline=True,
        zerolinewidth=1
    )

    return fig

# =====================================================
# Screening Scatter
# =====================================================

def screen_scatter(screen_df):

    if screen_df.empty:
        return px.scatter()

    plot_df = screen_df.copy()

    if "EconomicScore" in plot_df.columns:

        plot_df["BubbleSize"] = (
            plot_df["EconomicScore"]
            .fillna(1)
            .clip(lower=1)
            ** 0.5
        )

    else:

        plot_df["BubbleSize"] = (
            plot_df["Quality"]
            .fillna(1)
            .clip(lower=1)
            ** 0.5
        )

    fig = px.scatter(
        plot_df,
        x="Risk",
        y="EconomicScore",
        size="BubbleSize",
        size_max=45,
        color="EconomicScore",
        color_continuous_scale="RdYlGn",
        hover_name="Ticker",
        title="Screened Candidates"
    )

    fig.update_layout(
        height=700,
        xaxis_title="Forensic Risk",
        yaxis_title="Economic Score",
        coloraxis_colorbar_title="Economic Score",
        showlegend=False,
        hovermode="closest"
    )

    fig.update_xaxes(
        zeroline=True,
        zerolinewidth=1
    )

    fig.update_yaxes(
        zeroline=True,
        zerolinewidth=1
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
        hover_name="Ticker",
        title="Portfolio ROIC vs Economic Spread"
    )

    fig.update_layout(
        height=650,
        xaxis_title="ROIC-WACC",
        yaxis_title="ROIC",
        hovermode="closest"
    )

    fig.update_yaxes(
        tickformat=".0%"
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
