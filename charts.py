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

    roic_score = score_clip((roic / 0.50) * 100) if pd.notna(roic) else 0

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

    return {
        "ROIC Quality": roic_score,
        "Accrual Quality": accrual_score,
        "Cash Conversion": cfo_score,
        "SBC Discipline": sbc_score,
        "Risk Control": risk_score,
    }


def compare_radar(compare_df):

    categories = [
        "ROIC Quality",
        "Accrual Quality",
        "Cash Conversion",
        "SBC Discipline",
        "Risk Control",
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
        title="Quality Radar Score",
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
