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

    roic_score = (
        score_clip((roic / 0.50) * 100)
        if pd.notna(roic)
        else 0
    )

    accrual_score = (
        score_clip(100 - abs(accrual) * 500)
        if pd.notna(accrual)
        else 0
    )

    cfo_score = (
        score_clip((cfo / 1.5) * 100)
        if pd.notna(cfo)
        else 0
    )

    sbc_score = (
        score_clip(100 - sbc * 500)
        if pd.notna(sbc)
        else 0
    )

    risk_score = (
        score_clip(100 - risk)
        if pd.notna(risk)
        else 0
    )

    moat_score = score_clip(
        roic_score * 0.7 +
        risk_score * 0.3
    )

    capital_score = score_clip(
        roic_score * 0.5 +
        cfo_score * 0.5
    )

    shareholder_score = score_clip(
        sbc_score * 0.7 +
        risk_score * 0.3
    )

    return {
        "ROIC Quality": roic_score,
        "Accrual Quality": accrual_score,
        "Cash Conversion": cfo_score,
        "SBC Discipline": sbc_score,
        "Risk Control": risk_score,
        "Moat": moat_score,
        "Capital Allocation": capital_score,
        "Shareholder Yield": shareholder_score,
    }


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

        st.plotly_chart(
            fig,
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
        height=650
    )

    return fig


def compare_radar_v2(compare_df):

    categories = [
        "ROIC Quality",
        "Accrual Quality",
        "Cash Conversion",
        "SBC Discipline",
        "Risk Control",
        "Moat",
        "Capital Allocation",
        "Shareholder Yield"
    ]

    fig = go.Figure()

    for _, row in compare_df.iterrows():

        scores = quality_scores(row)

        values = [
            scores[c]
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
        title="8-Factor Quality Radar",
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


def screen_scatter(screen_df):

    if screen_df.empty:
        return px.scatter()

    fig = px.scatter(
        screen_df,
        x="Risk",
        y="ROIC",
        color="Grade",
        size="Quality",
        hover_name="Ticker",
        title="Screened Candidates"
    )

    return fig


def portfolio_scatter(df):

    if df.empty:
        return px.scatter()

    fig = px.scatter(
        df,
        x="Risk",
        y="ROIC",
        size="Weight",
        color="Grade",
        text="Ticker",
        hover_name="Ticker",
        title="Portfolio ROIC vs Risk"
    )

    fig.update_traces(
        textposition="top center"
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

    return fig
