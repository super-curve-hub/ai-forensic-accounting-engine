import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================================================

# Score Normalization

# ==========================================================

def score_clip(x, low=0, high=100):
if pd.isna(x):
return 0
return max(low, min(high, float(x)))

def quality_scores(row):

```
roic = row.get("ROIC", np.nan)
accrual = row.get("Accrual", np.nan)
cfo = row.get("CFO/NI", np.nan)
sbc = row.get("SBC/Revenue", np.nan)
risk = row.get("Risk", np.nan)

# ROIC
if pd.notna(roic):
    roic_score = score_clip((roic / 0.50) * 100)
else:
    roic_score = 0

# Accrual
if pd.notna(accrual):
    accrual_score = score_clip(
        100 - abs(accrual) * 500
    )
else:
    accrual_score = 0

# CFO conversion
if pd.notna(cfo):
    cfo_score = score_clip(
        (cfo / 1.5) * 100
    )
else:
    cfo_score = 0

# SBC burden
if pd.notna(sbc):
    sbc_score = score_clip(
        100 - sbc * 500
    )
else:
    sbc_score = 0

# Risk
if pd.notna(risk):
    risk_score = score_clip(
        100 - risk
    )
else:
    risk_score = 0

return {
    "ROIC Quality": roic_score,
    "Accrual Quality": accrual_score,
    "Cash Conversion": cfo_score,
    "SBC Discipline": sbc_score,
    "Risk Control": risk_score,
}
```

# ==========================================================

# Single Ticker Charts

# ==========================================================

def roic_chart(df):

```
tmp = df.copy()

if "ROIC_TTM" not in tmp.columns:
    return None

tmp["ROIC_pct"] = tmp["ROIC_TTM"] * 100

fig = px.line(
    tmp,
    x="date",
    y="ROIC_pct",
    title="ROIC Trend"
)

fig.update_layout(height=450)

return fig
```

def accrual_chart(df):

```
tmp = df.copy()

if "AccrualRatio" not in tmp.columns:
    return None

tmp["Accrual_pct"] = tmp["AccrualRatio"] * 100

fig = px.line(
    tmp,
    x="date",
    y="Accrual_pct",
    title="Accrual Trend"
)

fig.update_layout(height=450)

return fig
```

def risk_chart(df):

```
if "ForensicRiskScore" not in df.columns:
    return None

fig = px.bar(
    df,
    x="date",
    y="ForensicRiskScore",
    title="Forensic Risk Score"
)

fig.update_layout(height=450)

return fig
```

# ==========================================================

# Compare Bar Chart

# ==========================================================

def compare_bar(compare_df):

```
metrics = [
    "ROIC",
    "Accrual",
    "CFO/NI",
    "SBC/Revenue",
    "Risk"
]

melted = compare_df.melt(
    id_vars=["Ticker"],
    value_vars=[
        m for m in metrics
        if m in compare_df.columns
    ],
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

fig.update_layout(height=550)

return fig
```

# ==========================================================

# Quality Radar

# ==========================================================

def compare_radar(compare_df):

```
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
```

# ==========================================================

# Screening Scatter

# ==========================================================

def screening_scatter(screen_df):

```
if screen_df.empty:
    return None

fig = px.scatter(
    screen_df,
    x="Risk",
    y="ROIC",
    color="Grade",
    size="Quality",
    hover_name="Ticker",
    title="Screened Candidates: ROIC vs Risk"
)

fig.update_layout(height=650)

return fig
```

# ==========================================================

# Streamlit Helpers

# ==========================================================

def show_single_ticker_charts(df):

```
fig = roic_chart(df)
if fig:
    st.plotly_chart(
        fig,
        use_container_width=True
    )

fig = accrual_chart(df)
if fig:
    st.plotly_chart(
        fig,
        use_container_width=True
    )

fig = risk_chart(df)
if fig:
    st.plotly_chart(
        fig,
        use_container_width=True
    )
```

def show_compare_charts(compare_df):

```
st.plotly_chart(
    compare_bar(compare_df),
    use_container_width=True
)

st.plotly_chart(
    compare_radar(compare_df),
    use_container_width=True
)
```

def show_screening_chart(screen_df):

```
fig = screening_scatter(screen_df)

if fig:
    st.plotly_chart(
        fig,
        use_container_width=True
    )
```
