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

    return {
        "ROIC Quality":
            score_clip((roic / 0.50) * 100)
            if pd.notna(roic)
            else 0,

        "Accrual Quality":
            score_clip(100 - abs(accrual) * 500)
            if pd.notna(accrual)
            else 0,

        "Cash Conversion":
            score_clip((cfo / 1.5) * 100)
            if pd.notna(cfo)
            else 0,

        "SBC Discipline":
            score_clip(100 - sbc * 500)
            if pd.notna(sbc)
            else 0,

        "Risk Control":
            score_clip(100 - risk)
            if pd.notna(risk)
            else 0,
    }


def render_trend_charts(result):

    df = result["df"].copy()

    if "ROIC_TTM" in df.columns:

        tmp = df.copy()
        tmp["ROIC_pct"] = tmp["ROIC_TTM"] * 100

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
        tmp["Accrual_pct"] = tmp["AccrualRatio"] * 100

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


def compare_bar(compare_df):

    metrics = [
        "ROIC",
        "Accrual",
        "CFO/NI",
        "SBC/Revenue",
        "Risk"
    ]

    available = [
        m for m in metrics
        if m in compare_df.columns
    ]

    if not available:
        return px.bar()

    melted = compare_df.melt(
        id_vars=["Ticker"],
        value_vars=available,
        var_name="Metric",
        value_name="Value"
    )

    fig = px.bar(
        melted,
        x="Metric",
        y="Value",
        color="Ticker",
        barmode="group",
        title="Cross-Ticker Comparison"
    )

    return fig


def compare_radar(compare_df):

    categories = [
        "ROIC Quality",
        "Accrual Quality",
        "Cash Conversion",
        "SBC Discipline",
        "Risk Control"
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
        title="Quality Radar",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        height=700
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
