import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

def render_trend_charts(result):
    df = result["df"].copy()
    df["ROIC_pct"] = df["ROIC_TTM"] * 100
    df["Accrual_pct"] = df["AccrualRatio"] * 100
    df["Risk"] = df["ForensicRiskScore"]

    c1, c2 = st.columns(2)

    with c1:
        fig = px.line(df, x="date", y="ROIC_pct", title="ROIC trend")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.line(df, x="date", y="Accrual_pct", title="Accrual trend")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        fig = px.bar(df, x="date", y="Risk", title="Forensic risk trend")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        fig = px.line(df, x="date", y="DSO", title="DSO")
        st.plotly_chart(fig, use_container_width=True)

def compare_bar(compare_df):
    metrics = ["ROIC", "Accrual", "CFO/NI", "SBC/Revenue", "Risk"]
    available = [m for m in metrics if m in compare_df.columns]

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
        title="Cross-ticker comparison"
    )

    return fig

def compare_radar(compare_df):
    categories = ["ROIC", "Accrual", "CFO/NI", "SBC/Revenue", "Risk"]
    fig = go.Figure()

    for _, row in compare_df.iterrows():
        values = []
        for c in categories:
            v = row.get(c)
            if pd.isna(v):
                v = 0
            if c == "Risk":
                v = max(0, 1 - v / 100)
            elif c in ["Accrual", "SBC/Revenue"]:
                v = max(0, 1 - abs(v))
            else:
                v = max(0, min(float(v), 1))
            values.append(v)

        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=row.get("Ticker", "NA")
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title="Quality radar"
    )

    return fig

def screen_scatter(screen_df):
    return px.scatter(
        screen_df,
        x="Risk",
        y="ROIC",
        size="Quality",
        color="Grade",
        hover_name="Ticker",
        title="Screened candidates: ROIC vs Risk"
    )
