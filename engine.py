import numpy as np
import pandas as pd
import streamlit as st

from sec_loader import ticker_to_cik, load_companyfacts, build_statement_dataframe
from utils import safe_div, forensic_grade, regime_label

@st.cache_data(ttl=3600, show_spinner=False)
def run_forensic_engine(ticker, wacc=0.10):
    ticker = ticker.upper().strip()
    cik, company = ticker_to_cik(ticker)

    facts = load_companyfacts(cik)
    df, used_tags = build_statement_dataframe(facts)

    for col in ["Cash", "SBC", "OperatingLeaseLiability", "DeferredRevenue"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    flow_cols = [
        "Revenue", "COGS", "OperatingIncome", "PretaxIncome", "IncomeTax",
        "NetIncome", "CFO", "Capex", "SBC"
    ]

    for col in flow_cols:
        df[f"{col}_TTM"] = pd.to_numeric(df[col], errors="coerce").rolling(4, min_periods=4).sum()

    df["TaxRate"] = safe_div(df["IncomeTax_TTM"], df["PretaxIncome_TTM"])
    df["TaxRate"] = (
        df["TaxRate"]
        .replace([np.inf, -np.inf], np.nan)
        .clip(lower=0, upper=0.35)
        .fillna(0.21)
    )

    df["NOPAT_TTM"] = df["OperatingIncome_TTM"] * (1 - df["TaxRate"])
    df["NOPAT_TTM"] = df["NOPAT_TTM"].fillna(df["PretaxIncome_TTM"] * (1 - df["TaxRate"]))

    df["InvestedCapital"] = (
        pd.to_numeric(df["Equity"], errors="coerce").fillna(0)
        + pd.to_numeric(df["Liabilities"], errors="coerce").fillna(0)
        - pd.to_numeric(df["Cash"], errors="coerce").fillna(0)
        + pd.to_numeric(df["OperatingLeaseLiability"], errors="coerce").fillna(0)
    )

    df["InvestedCapital"] = df["InvestedCapital"].replace(0, np.nan)
    df["AvgIC"] = df["InvestedCapital"].rolling(2, min_periods=2).mean()

    df["ROIC_TTM"] = safe_div(df["NOPAT_TTM"], df["AvgIC"])
    df["ROIC_WACC_Spread"] = df["ROIC_TTM"] - wacc
    df["EconomicEarnings_TTM"] = df["NOPAT_TTM"] - wacc * df["AvgIC"]

    df["Accruals_TTM"] = df["NetIncome_TTM"] - df["CFO_TTM"]
    df["AvgAssets"] = pd.to_numeric(df["Assets"], errors="coerce").rolling(2, min_periods=2).mean()
    df["AccrualRatio"] = safe_div(df["Accruals_TTM"], df["AvgAssets"])

    df["CFO_to_NI"] = safe_div(df["CFO_TTM"], df["NetIncome_TTM"])
    df["FCF_TTM"] = df["CFO_TTM"] - df["Capex_TTM"].abs()
    df["FCF_to_NI"] = safe_div(df["FCF_TTM"], df["NetIncome_TTM"])
    df["SBC_to_Revenue"] = safe_div(df["SBC_TTM"], df["Revenue_TTM"])

    receivables = pd.to_numeric(df["Receivables"], errors="coerce")
    inventory = pd.to_numeric(df["Inventory"], errors="coerce")

    df["DSO"] = np.nan if receivables.isna().all() else safe_div(receivables, df["Revenue_TTM"] / 365)
    df["InventoryDays"] = (
        np.nan
        if inventory.isna().all() or df["COGS_TTM"].isna().all()
        else safe_div(inventory, df["COGS_TTM"] / 365)
    )

    scores = []
    flags = []

    for _, row in df.iterrows():
        score = 0
        f = []

        if pd.notna(row["AccrualRatio"]):
            if row["AccrualRatio"] > 0.10:
                score += 25
                f.append("Accrual distortion severe")
            elif row["AccrualRatio"] > 0.05:
                score += 15
                f.append("Accrual distortion moderate")

        if pd.notna(row["CFO_to_NI"]) and row["NetIncome_TTM"] > 0:
            if row["CFO_to_NI"] < 0.80:
                score += 20
                f.append("Weak CFO conversion")
            elif row["CFO_to_NI"] < 1.00:
                score += 10
                f.append("CFO below NI")

        if pd.notna(row["SBC_to_Revenue"]):
            if row["SBC_to_Revenue"] > 0.15:
                score += 20
                f.append("High SBC burden")
            elif row["SBC_to_Revenue"] > 0.08:
                score += 10
                f.append("Moderate SBC burden")

        if pd.notna(row["DSO"]):
            if row["DSO"] > 90:
                score += 15
                f.append("High DSO")
            elif row["DSO"] > 60:
                score += 10
                f.append("Moderate DSO")

        if pd.notna(row["InventoryDays"]):
            if row["InventoryDays"] > 120:
                score += 15
                f.append("Inventory buildup")
            elif row["InventoryDays"] > 90:
                score += 10
                f.append("Moderate inventory buildup")

        if pd.notna(row["ROIC_WACC_Spread"]) and row["ROIC_WACC_Spread"] < 0:
            score += 15
            f.append("ROIC below WACC")

        scores.append(min(score, 100))
        flags.append("; ".join(f) if f else "No major red flags")

    df["ForensicRiskScore"] = scores
    df["QualityScore"] = 100 - df["ForensicRiskScore"]
    df["Flags"] = flags

    valid = df.dropna(subset=["ROIC_TTM", "AccrualRatio"], how="all")
    latest = (df.iloc[-1] if valid.empty else valid.iloc[-1]).to_dict()

    latest.update({
        "Ticker": ticker,
        "Company": company,
        "CIK": cik,
        "Grade": forensic_grade(latest.get("ForensicRiskScore", np.nan)),
    })

    latest["Regime"] = regime_label(latest)

    return {
        "ticker": ticker,
        "company": company,
        "cik": cik,
        "df": df,
        "latest": latest,
        "used_tags": used_tags,
    }
