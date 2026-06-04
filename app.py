import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px

st.set_page_config(
    page_title="AI Forensic Accounting Engine",
    layout="wide"
)

st.title("AI Forensic Accounting Engine")

ticker = st.text_input("Ticker", "NVDA")

USER_AGENT = "your_email@example.com"

headers = {
    "User-Agent": USER_AGENT
}

def safe_div(a, b):

    out = a / b

    out = out.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return out

if st.button("Analyze"):

    ticker_url = "https://www.sec.gov/files/company_tickers.json"

    tickers = requests.get(
        ticker_url,
        headers=headers
    ).json()

    ticker_df = pd.DataFrame(tickers).T

    ticker_df["ticker"] = (
        ticker_df["ticker"]
        .str.upper()
    )

    row = ticker_df[
        ticker_df["ticker"] == ticker.upper()
    ]

    if row.empty:
        st.error("Ticker not found")
        st.stop()

    cik = str(row.iloc[0]["cik_str"]).zfill(10)

    company_name = row.iloc[0]["title"]

    st.subheader(company_name)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    data = requests.get(
        url,
        headers=headers
    ).json()

    facts = data.get("facts", {}).get("us-gaap", {})

    def get_fact(tag):

        if tag not in facts:
            return pd.DataFrame()

        units = facts[tag].get("units", {})

        frames = []

        for unit, vals in units.items():

            temp = pd.DataFrame(vals)

            if temp.empty:
                continue

            temp["tag"] = tag
            temp["unit"] = unit

            frames.append(temp)

        if not frames:
            return pd.DataFrame()

        return pd.concat(frames, ignore_index=True)

    def quarterly_series(tag):

        df = get_fact(tag)

        if df.empty:
            return pd.DataFrame(columns=["date", tag])

        required = {"form", "unit", "end", "val"}

        if not required.issubset(set(df.columns)):
            return pd.DataFrame(columns=["date", tag])

        temp = df[
            (df["form"].isin(["10-Q", "10-K"])) &
            (df["unit"] == "USD")
        ].copy()

        if temp.empty:
            return pd.DataFrame(columns=["date", tag])

        temp["date"] = pd.to_datetime(
            temp["end"],
            errors="coerce"
        )

        temp = (
            temp.sort_values("date")
            .drop_duplicates("date", keep="last")
        )

        return temp[["date", "val"]].rename(
            columns={"val": tag}
        )

    TAGS = {

        "Revenue": "RevenueFromContractWithCustomerExcludingAssessedTax",

        "OperatingIncome": "OperatingIncomeLoss",

        "NetIncome": "NetIncomeLoss",

        "CFO": "NetCashProvidedByUsedInOperatingActivities",

        "Assets": "Assets",

        "Liabilities": "Liabilities",

        "Equity": "StockholdersEquity",

        "Cash": "CashAndCashEquivalentsAtCarryingValue",

        "Receivables": "AccountsReceivableNetCurrent",

        "Inventory": "InventoryNet",

        "SBC": "ShareBasedCompensation"

    }

    master = None

    for metric, tag in TAGS.items():

        s = quarterly_series(tag)

        if s.empty:
            continue

        s = s.rename(columns={tag: metric})

        if master is None:
            master = s
        else:
            master = master.merge(
                s,
                on="date",
                how="outer"
            )

    df = master.sort_values("date")

    for col in df.columns:

        if col != "date":
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    flow_cols = [
        "Revenue",
        "OperatingIncome",
        "NetIncome",
        "CFO",
        "SBC"
    ]

    for col in flow_cols:

        df[f"{col}_TTM"] = (
            df[col]
            .rolling(4)
            .sum()
        )

    df["NOPAT_TTM"] = (
        df["OperatingIncome_TTM"] *
        (1 - 0.21)
    )

    df["InvestedCapital"] = (
        df["Equity"]
        + df["Liabilities"]
        - df["Cash"]
    )

    df["AvgIC"] = (
        df["InvestedCapital"]
        .rolling(2)
        .mean()
    )

    df["ROIC_TTM"] = safe_div(
        df["NOPAT_TTM"],
        df["AvgIC"]
    )

    df["Accruals"] = (
        df["NetIncome_TTM"] -
        df["CFO_TTM"]
    )

    df["AvgAssets"] = (
        df["Assets"]
        .rolling(2)
        .mean()
    )

    df["AccrualRatio"] = safe_div(
        df["Accruals"],
        df["AvgAssets"]
    )

    df["CFO_to_NI"] = safe_div(
        df["CFO_TTM"],
        df["NetIncome_TTM"]
    )

    df["SBC_to_Revenue"] = safe_div(
        df["SBC_TTM"],
        df["Revenue_TTM"]
    )

    df["DSO"] = safe_div(
        df["Receivables"],
        df["Revenue_TTM"] / 365
    )

    df["InventoryDays"] = safe_div(
        df["Inventory"],
        df["Revenue_TTM"] / 365
    )

    scores = []

    for idx, row in df.iterrows():

        score = 0

        if pd.notna(row["AccrualRatio"]):

            if row["AccrualRatio"] > 0.10:
                score += 25

        if pd.notna(row["CFO_to_NI"]):

            if row["CFO_to_NI"] < 0.8:
                score += 20

        scores.append(min(score, 100))

    df["ForensicRiskScore"] = scores

    latest = df.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "ROIC",
        f"{latest['ROIC_TTM']*100:.1f}%"
    )

    col2.metric(
        "Accrual Ratio",
        f"{latest['AccrualRatio']*100:.1f}%"
    )

    col3.metric(
        "DSO",
        f"{latest['DSO']:.1f}"
    )

    col4.metric(
        "Risk Score",
        f"{latest['ForensicRiskScore']}"
    )

    st.subheader("Forensic Dashboard")

    st.dataframe(df.tail(12))

    fig1 = px.line(
        df,
        x="date",
        y=df["ROIC_TTM"] * 100,
        title="ROIC"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    fig2 = px.line(
        df,
        x="date",
        y="DSO",
        title="DSO"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    fig3 = px.bar(
        df,
        x="date",
        y="ForensicRiskScore",
        title="Forensic Risk Score"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )
