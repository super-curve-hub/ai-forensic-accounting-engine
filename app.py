import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px

# ============================================================
# AI FORENSIC ACCOUNTING ENGINE v1.3
# Streamlit Version
#
# Fixes:
# - Missing XBRL tags no longer crash the app
# - Receivables / Inventory / Cash / Equity etc. are auto-created if absent
# - Basic tag fallback hierarchy
# - Safer latest-row selection
# - Clear warning when data is insufficient
# ============================================================

st.set_page_config(
    page_title="AI Forensic Accounting Engine",
    layout="wide"
)

st.title("AI Forensic Accounting Engine")
st.caption("SEC 10-K / 10-Q based forensic accounting dashboard")

ticker = st.text_input("Ticker", "NVDA").upper().strip()
wacc = st.number_input("WACC", min_value=0.00, max_value=0.30, value=0.10, step=0.01)

# SEC requires a User-Agent.
# You can replace this with your real email.
USER_AGENT = "your_email@example.com"
headers = {"User-Agent": USER_AGENT}


def safe_div(a, b):
    out = a / b
    if isinstance(out, pd.Series):
        out = out.replace([np.inf, -np.inf], np.nan)
    elif np.isinf(out):
        out = np.nan
    return out


def get_sec_json(url):
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"SEC request failed: {r.status_code}")
    return r.json()


if st.button("Analyze"):

    try:
        # ========================================================
        # TICKER -> CIK
        # ========================================================

        ticker_url = "https://www.sec.gov/files/company_tickers.json"
        tickers = get_sec_json(ticker_url)

        ticker_df = pd.DataFrame(tickers).T
        ticker_df["ticker"] = ticker_df["ticker"].str.upper()

        row = ticker_df[ticker_df["ticker"] == ticker]

        if row.empty:
            st.error(f"Ticker not found: {ticker}")
            st.stop()

        cik = str(row.iloc[0]["cik_str"]).zfill(10)
        company_name = row.iloc[0]["title"]

        st.subheader(company_name)
        st.caption(f"Ticker: {ticker} | CIK: {cik}")

        # ========================================================
        # COMPANYFACTS
        # ========================================================

        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        data = get_sec_json(url)

        facts = data.get("facts", {}).get("us-gaap", {})

        if not facts:
            st.error("No us-gaap facts found for this company.")
            st.stop()

        # ========================================================
        # HELPERS
        # ========================================================

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


        def series_for_tag(tag):
            raw = get_fact(tag)

            if raw.empty:
                return pd.DataFrame(columns=["date", tag])

            required = {"form", "unit", "end", "val"}
            if not required.issubset(set(raw.columns)):
                return pd.DataFrame(columns=["date", tag])

            temp = raw[
                (raw["form"].isin(["10-Q", "10-Q/A", "10-K", "10-K/A"])) &
                (raw["unit"] == "USD")
            ].copy()

            if temp.empty:
                return pd.DataFrame(columns=["date", tag])

            temp["date"] = pd.to_datetime(temp["end"], errors="coerce")
            temp["filed"] = pd.to_datetime(temp.get("filed"), errors="coerce")

            temp = temp.dropna(subset=["date"])

            # Same end-date can appear multiple times. Keep the latest filing.
            temp = (
                temp.sort_values(["date", "filed"])
                .drop_duplicates("date", keep="last")
            )

            return temp[["date", "val"]].rename(columns={"val": tag})


        def resolve_metric(metric_name, tag_candidates):
            best = None
            best_tag = None
            best_count = -1

            for tag in tag_candidates:
                s = series_for_tag(tag)

                if s.empty:
                    continue

                count = s[tag].notna().sum()

                if count > best_count:
                    best = s
                    best_tag = tag
                    best_count = count

            if best is None:
                return pd.DataFrame(columns=["date", metric_name]), None

            return best.rename(columns={best_tag: metric_name}), best_tag


        # ========================================================
        # TAG MAP
        # ========================================================

        TAG_MAP = {
            "Revenue": [
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet",
                "Revenues"
            ],
            "OperatingIncome": [
                "OperatingIncomeLoss",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
            ],
            "PretaxIncome": [
                "IncomeBeforeTaxExpenseBenefit",
                "IncomeBeforeIncomeTaxes",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
            ],
            "IncomeTax": [
                "IncomeTaxExpenseBenefit",
                "CurrentIncomeTaxExpenseBenefit",
                "IncomeTaxesPaidNet"
            ],
            "NetIncome": [
                "NetIncomeLoss",
                "ProfitLoss"
            ],
            "CFO": [
                "NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"
            ],
            "Capex": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquireProductiveAssets",
                "CapitalExpendituresIncurredButNotYetPaid"
            ],
            "Assets": [
                "Assets"
            ],
            "Liabilities": [
                "Liabilities"
            ],
            "Equity": [
                "StockholdersEquity",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
            ],
            "Cash": [
                "CashAndCashEquivalentsAtCarryingValue",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
            ],
            "Receivables": [
                "AccountsReceivableNetCurrent",
                "AccountsReceivableNet",
                "ReceivablesNetCurrent",
                "ReceivablesNet"
            ],
            "Inventory": [
                "InventoryNet",
                "InventoryFinishedGoodsNetOfReserves",
                "InventoryRawMaterialsAndPurchasedPartsNetOfReserves"
            ],
            "SBC": [
                "ShareBasedCompensation",
                "ShareBasedCompensationArrangementByShareBasedPaymentAwardExpense"
            ],
            "OperatingLeaseLiability": [
                "OperatingLeaseLiability",
                "OperatingLeaseLiabilityCurrent",
                "OperatingLeaseLiabilityNoncurrent"
            ],
            "DeferredRevenue": [
                "ContractWithCustomerLiabilityCurrent",
                "DeferredRevenueCurrent",
                "DeferredRevenueAndCreditsCurrent"
            ]
        }

        # ========================================================
        # BUILD DATAFRAME
        # ========================================================

        master = None
        used_tags = {}

        for metric, candidates in TAG_MAP.items():
            s, used_tag = resolve_metric(metric, candidates)
            used_tags[metric] = used_tag if used_tag else "NOT FOUND"

            if s.empty:
                continue

            if master is None:
                master = s
            else:
                master = master.merge(s, on="date", how="outer")

        if master is None or master.empty:
            st.error("No usable financial facts found.")
            st.stop()

        df = master.sort_values("date").reset_index(drop=True)

        for col in df.columns:
            if col != "date":
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ========================================================
        # REQUIRED COLUMNS
        # ========================================================

        required_cols = [
            "Revenue",
            "OperatingIncome",
            "PretaxIncome",
            "IncomeTax",
            "NetIncome",
            "CFO",
            "Capex",
            "Assets",
            "Liabilities",
            "Equity",
            "Cash",
            "Receivables",
            "Inventory",
            "SBC",
            "OperatingLeaseLiability",
            "DeferredRevenue"
        ]

        for col in required_cols:
            if col not in df.columns:
                df[col] = np.nan

        # Some missing balance sheet items can be zero for ratio safety.
        for col in ["Cash", "Receivables", "Inventory", "SBC", "OperatingLeaseLiability", "DeferredRevenue"]:
            df[col] = df[col].fillna(0)

        # ========================================================
        # TTM CALCULATIONS
        # Note: SEC companyfacts may mix quarterly and YTD values.
        # This is a pragmatic v1.3 approximation, not full quarterization.
        # ========================================================

        flow_cols = [
            "Revenue",
            "OperatingIncome",
            "PretaxIncome",
            "IncomeTax",
            "NetIncome",
            "CFO",
            "Capex",
            "SBC"
        ]

        for col in flow_cols:
            df[f"{col}_TTM"] = df[col].rolling(4, min_periods=4).sum()

        # Tax rate
        df["TaxRate"] = safe_div(df["IncomeTax_TTM"], df["PretaxIncome_TTM"])
        df["TaxRate"] = (
            df["TaxRate"]
            .replace([np.inf, -np.inf], np.nan)
            .clip(lower=0, upper=0.35)
            .fillna(0.21)
        )

        # NOPAT
        df["NOPAT_TTM"] = df["OperatingIncome_TTM"] * (1 - df["TaxRate"])
        df["NOPAT_TTM"] = df["NOPAT_TTM"].fillna(df["PretaxIncome_TTM"] * (1 - df["TaxRate"]))

        # Invested capital
        df["InvestedCapital"] = (
            df["Equity"].fillna(0)
            + df["Liabilities"].fillna(0)
            - df["Cash"].fillna(0)
            + df["OperatingLeaseLiability"].fillna(0)
        )

        df["InvestedCapital"] = df["InvestedCapital"].replace(0, np.nan)
        df["AvgIC"] = df["InvestedCapital"].rolling(2, min_periods=2).mean()

        # Core metrics
        df["ROIC_TTM"] = safe_div(df["NOPAT_TTM"], df["AvgIC"])
        df["ROIC_WACC_Spread"] = df["ROIC_TTM"] - wacc
        df["EconomicEarnings_TTM"] = df["NOPAT_TTM"] - wacc * df["AvgIC"]

        # Accruals
        df["Accruals_TTM"] = df["NetIncome_TTM"] - df["CFO_TTM"]
        df["AvgAssets"] = df["Assets"].rolling(2, min_periods=2).mean()
        df["AccrualRatio"] = safe_div(df["Accruals_TTM"], df["AvgAssets"])

        # Cash conversion
        df["CFO_to_NI"] = safe_div(df["CFO_TTM"], df["NetIncome_TTM"])
        df["FCF_TTM"] = df["CFO_TTM"] - df["Capex_TTM"].abs()
        df["FCF_to_NI"] = safe_div(df["FCF_TTM"], df["NetIncome_TTM"])

        # Quality ratios
        df["SBC_to_Revenue"] = safe_div(df["SBC_TTM"], df["Revenue_TTM"])
        df["DSO"] = safe_div(df["Receivables"], df["Revenue_TTM"] / 365)
        df["InventoryDays"] = safe_div(df["Inventory"], df["Revenue_TTM"] / 365)

        # ========================================================
        # FORENSIC SCORE
        # ========================================================

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

            if pd.notna(row["ROIC_WACC_Spread"]):
                if row["ROIC_WACC_Spread"] < 0:
                    score += 15
                    f.append("ROIC below WACC")

            scores.append(min(score, 100))
            flags.append("; ".join(f) if f else "No major red flags")

        df["ForensicRiskScore"] = scores
        df["QualityScore"] = 100 - df["ForensicRiskScore"]
        df["Flags"] = flags

        # Use the latest row with enough calculated data.
        valid = df.dropna(subset=["ROIC_TTM", "AccrualRatio"], how="all")

        if valid.empty:
            st.warning("Data loaded, but insufficient calculated TTM metrics for this ticker.")
            latest = df.iloc[-1]
        else:
            latest = valid.iloc[-1]

        # ========================================================
        # KPI
        # ========================================================

        def pct_fmt(x):
            return "NA" if pd.isna(x) else f"{x * 100:.1f}%"

        def num_fmt(x):
            return "NA" if pd.isna(x) else f"{x:.1f}"

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("ROIC", pct_fmt(latest.get("ROIC_TTM")))
        c2.metric("Accrual Ratio", pct_fmt(latest.get("AccrualRatio")))
        c3.metric("CFO / NI", num_fmt(latest.get("CFO_to_NI")))
        c4.metric("DSO", num_fmt(latest.get("DSO")))
        c5.metric("Risk Score", "NA" if pd.isna(latest.get("ForensicRiskScore")) else int(latest.get("ForensicRiskScore")))

        st.info(f"Flags: {latest.get('Flags', 'NA')}")

        # ========================================================
        # TABLES
        # ========================================================

        with st.expander("Resolved XBRL Tags"):
            st.dataframe(pd.DataFrame(
                [{"Metric": k, "ResolvedTag": v} for k, v in used_tags.items()]
            ), use_container_width=True)

        display_cols = [
            "date",
            "Revenue_TTM",
            "NOPAT_TTM",
            "ROIC_TTM",
            "ROIC_WACC_Spread",
            "EconomicEarnings_TTM",
            "AccrualRatio",
            "CFO_to_NI",
            "FCF_to_NI",
            "SBC_to_Revenue",
            "DSO",
            "InventoryDays",
            "ForensicRiskScore",
            "QualityScore",
            "Flags"
        ]

        existing_display_cols = [c for c in display_cols if c in df.columns]

        st.subheader("Forensic Dashboard")
        st.dataframe(df[existing_display_cols].tail(20), use_container_width=True)

        # ========================================================
        # CHARTS
        # ========================================================

        plot_df = df.copy()
        plot_df["ROIC_pct"] = plot_df["ROIC_TTM"] * 100
        plot_df["Accrual_pct"] = plot_df["AccrualRatio"] * 100
        plot_df["SBC_pct"] = plot_df["SBC_to_Revenue"] * 100

        st.subheader("Charts")

        fig1 = px.line(plot_df, x="date", y="ROIC_pct", title="ROIC")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.line(plot_df, x="date", y="Accrual_pct", title="Accrual Ratio")
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.line(plot_df, x="date", y="DSO", title="DSO")
        st.plotly_chart(fig3, use_container_width=True)

        fig4 = px.line(plot_df, x="date", y="InventoryDays", title="Inventory Days")
        st.plotly_chart(fig4, use_container_width=True)

        fig5 = px.bar(plot_df, x="date", y="ForensicRiskScore", title="Forensic Risk Score")
        st.plotly_chart(fig5, use_container_width=True)

        st.caption("Note: v1.3 uses pragmatic TTM approximation from SEC companyfacts. Full quarterization is planned for v1.4.")

    except Exception as e:
        st.error("The app encountered an error.")
        st.exception(e)
