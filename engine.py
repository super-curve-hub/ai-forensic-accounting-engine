import pandas as pd
import numpy as np
import requests
import streamlit as st


USER_AGENT = "i.love.melonpan@gmail.com"
SEC_HEADERS = {
    "User-Agent": USER_AGENT
}


def safe_div(a, b):
    try:
        out = a / b

        if isinstance(out, pd.Series):
            return out.replace(
                [np.inf, -np.inf],
                np.nan
            )

        if np.isinf(out):
            return np.nan

        return out

    except Exception:
        return np.nan


@st.cache_data(ttl=86400, show_spinner=False)
def get_sec_json(url):
    response = requests.get(
        url,
        headers=SEC_HEADERS,
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"SEC request failed: {response.status_code}"
        )

    return response.json()


@st.cache_data(ttl=86400, show_spinner=False)
def ticker_map():
    data = get_sec_json(
        "https://www.sec.gov/files/company_tickers.json"
    )

    df = pd.DataFrame(data).T

    df["ticker"] = (
        df["ticker"]
        .astype(str)
        .str.upper()
    )

    return df


def ticker_to_cik(ticker):
    ticker = ticker.upper().strip()

    df = ticker_map()

    row = df[
        df["ticker"] == ticker
    ]

    if row.empty:
        raise ValueError(
            f"Ticker not found: {ticker}"
        )

    cik = str(
        row.iloc[0]["cik_str"]
    ).zfill(10)

    company = row.iloc[0]["title"]

    return cik, company


def get_fact_frame(facts, tag):
    if tag not in facts:
        return pd.DataFrame()

    units = facts[tag].get(
        "units",
        {}
    )

    frames = []

    for unit, values in units.items():

        tmp = pd.DataFrame(values)

        if tmp.empty:
            continue

        tmp["tag"] = tag
        tmp["unit"] = unit

        frames.append(tmp)

    if not frames:
        return pd.DataFrame()

    return pd.concat(
        frames,
        ignore_index=True
    )


def fact_series(facts, tag):
    raw = get_fact_frame(
        facts,
        tag
    )

    if raw.empty:
        return pd.DataFrame(
            columns=[
                "date",
                tag,
                f"{tag}_form",
                f"{tag}_filed"
            ]
        )

    required = {
        "form",
        "unit",
        "end",
        "val"
    }

    if not required.issubset(
        set(raw.columns)
    ):
        return pd.DataFrame(
            columns=[
                "date",
                tag,
                f"{tag}_form",
                f"{tag}_filed"
            ]
        )

    tmp = raw[
        raw["form"].isin(
            [
                "10-Q",
                "10-Q/A",
                "10-K",
                "10-K/A"
            ]
        )
        &
        raw["unit"].isin(
            [
                "USD",
                "shares",
                "USD/shares"
            ]
        )
    ].copy()

    if tmp.empty:
        return pd.DataFrame(
            columns=[
                "date",
                tag,
                f"{tag}_form",
                f"{tag}_filed"
            ]
        )

    tmp["date"] = pd.to_datetime(
        tmp["end"],
        errors="coerce"
    )

    tmp["filed_date"] = pd.to_datetime(
        tmp.get("filed"),
        errors="coerce"
    )

    tmp = tmp.dropna(
        subset=["date"]
    )

    tmp = tmp.sort_values(
        [
            "date",
            "filed_date"
        ]
    )

    tmp = tmp.drop_duplicates(
        subset=["date"],
        keep="last"
    )

    out = tmp[
        [
            "date",
            "val",
            "form",
            "filed_date"
        ]
    ].copy()

    out = out.rename(
        columns={
            "val": tag,
            "form": f"{tag}_form",
            "filed_date": f"{tag}_filed"
        }
    )

    return out


def resolve_metric(
    facts,
    metric,
    candidates
):
    best = None
    best_tag = None
    best_count = -1

    for tag in candidates:

        s = fact_series(
            facts,
            tag
        )

        if s.empty:
            continue

        count = s[tag].notna().sum()

        if count > best_count:
            best = s
            best_tag = tag
            best_count = count

    if best is None:
        return (
            pd.DataFrame(
                columns=["date", metric]
            ),
            "NOT FOUND"
        )

    rename_map = {
        best_tag: metric,
        f"{best_tag}_form": f"{metric}_form",
        f"{best_tag}_filed": f"{metric}_filed"
    }

    best = best.rename(
        columns=rename_map
    )

    keep_cols = [
        c
        for c in [
            "date",
            metric,
            f"{metric}_form",
            f"{metric}_filed"
        ]
        if c in best.columns
    ]

    return best[keep_cols], best_tag


def build_master_frame(
    facts,
    tag_map
):
    master = None
    used_tags = {}

    for metric, candidates in tag_map.items():

        series, tag = resolve_metric(
            facts,
            metric,
            candidates
        )

        used_tags[metric] = tag

        if series.empty:
            continue

        if master is None:
            master = series
        else:
            master = master.merge(
                series,
                on="date",
                how="outer"
            )

    if master is None or master.empty:
        raise RuntimeError(
            "No usable financial facts found."
        )

    master = master.sort_values(
        "date"
    )

    master = master.drop_duplicates(
        subset=["date"],
        keep="last"
    )

    master = master.reset_index(
        drop=True
    )

    return master, used_tags


def forensic_grade(score):
    if pd.isna(score):
        return "NA"

    if score <= 20:
        return "A"

    if score <= 40:
        return "B"

    if score <= 60:
        return "C"

    if score <= 80:
        return "D"

    return "F"


def regime_label(latest):
    roic = latest.get(
        "ROIC_TTM",
        np.nan
    )

    spread = latest.get(
        "ROIC_WACC_Spread",
        np.nan
    )

    accrual = latest.get(
        "AccrualRatio",
        np.nan
    )

    cfo = latest.get(
        "CFO_to_NI",
        np.nan
    )

    risk = latest.get(
        "ForensicRiskScore",
        np.nan
    )

    sbc = latest.get(
        "SBC_to_Revenue",
        np.nan
    )

    if (
        pd.notna(spread)
        and pd.notna(accrual)
        and pd.notna(cfo)
        and pd.notna(risk)
        and spread > 0
        and accrual < 0
        and cfo > 1
        and risk <= 20
    ):
        return "Quality Compounder"

    if (
        pd.notna(spread)
        and spread < 0
    ):
        return "Value Destruction"

    if (
        pd.notna(sbc)
        and sbc > 0.15
    ):
        return "High SBC Growth"

    if (
        pd.notna(accrual)
        and accrual > 0.10
    ):
        return "Accrual Stress"

    if (
        pd.notna(roic)
        and roic > 0.20
        and pd.notna(risk)
        and risk <= 40
    ):
        return "High ROIC / Monitor"

    return "Neutral / Inconclusive"


@st.cache_data(ttl=3600, show_spinner=False)
def run_forensic_engine(
    ticker,
    wacc=0.10
):
    ticker = ticker.upper().strip()

    cik, company = ticker_to_cik(
        ticker
    )

    data = get_sec_json(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    )

    facts = (
        data
        .get("facts", {})
        .get("us-gaap", {})
    )

    if not facts:
        raise RuntimeError(
            "No us-gaap facts found."
        )

    tag_map = {
        "Revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
            "Revenues"
        ],
        "COGS": [
            "CostOfRevenue",
            "CostOfGoodsAndServicesSold",
            "CostOfGoodsSold"
        ],
        "GrossProfit": [
            "GrossProfit"
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
        ],
        "Buyback": [
            "PaymentsForRepurchaseOfCommonStock",
            "PaymentsForRepurchaseOfEquity"
        ]
    }

    df, used_tags = build_master_frame(
        facts,
        tag_map
    )

    for col in df.columns:
        if (
            col != "date"
            and not col.endswith("_form")
            and not col.endswith("_filed")
        ):
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    required = [
        "Revenue",
        "COGS",
        "GrossProfit",
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
        "DeferredRevenue",
        "Buyback"
    ]

    for col in required:
        if col not in df.columns:
            df[col] = np.nan

    for col in [
        "Cash",
        "SBC",
        "OperatingLeaseLiability",
        "DeferredRevenue",
        "Buyback"
    ]:
        df[col] = df[col].fillna(0)

    flow_cols = [
        "Revenue",
        "COGS",
        "GrossProfit",
        "OperatingIncome",
        "PretaxIncome",
        "IncomeTax",
        "NetIncome",
        "CFO",
        "Capex",
        "SBC",
        "Buyback"
    ]

    for col in flow_cols:
        df[f"{col}_TTM"] = (
            df[col]
            .rolling(
                4,
                min_periods=4
            )
            .sum()
        )

    df["TaxRate"] = safe_div(
        df["IncomeTax_TTM"],
        df["PretaxIncome_TTM"]
    )

    df["TaxRate"] = (
        df["TaxRate"]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .clip(0, 0.35)
        .fillna(0.21)
    )

    df["NOPAT_TTM"] = (
        df["OperatingIncome_TTM"]
        *
        (
            1 - df["TaxRate"]
        )
    )

    df["NOPAT_TTM"] = df["NOPAT_TTM"].fillna(
        df["PretaxIncome_TTM"]
        *
        (
            1 - df["TaxRate"]
        )
    )

    df["InvestedCapital"] = (
        df["Equity"].fillna(0)
        +
        df["Liabilities"].fillna(0)
        -
        df["Cash"].fillna(0)
        +
        df["OperatingLeaseLiability"].fillna(0)
    )

    df["InvestedCapital"] = (
        df["InvestedCapital"]
        .replace(0, np.nan)
    )

    df["AvgIC"] = (
        df["InvestedCapital"]
        .rolling(
            2,
            min_periods=2
        )
        .mean()
    )

    df["ROIC_TTM"] = safe_div(
        df["NOPAT_TTM"],
        df["AvgIC"]
    )

    df["ROIC_WACC_Spread"] = (
        df["ROIC_TTM"]
        -
        wacc
    )

    df["EconomicEarnings_TTM"] = (
        df["NOPAT_TTM"]
        -
        wacc * df["AvgIC"]
    )

    df["Accruals_TTM"] = (
        df["NetIncome_TTM"]
        -
        df["CFO_TTM"]
    )

    df["AvgAssets"] = (
        df["Assets"]
        .rolling(
            2,
            min_periods=2
        )
        .mean()
    )

    df["AccrualRatio"] = safe_div(
        df["Accruals_TTM"],
        df["AvgAssets"]
    )

    df["CFO_to_NI"] = safe_div(
        df["CFO_TTM"],
        df["NetIncome_TTM"]
    )

    df["FCF_TTM"] = (
        df["CFO_TTM"]
        -
        df["Capex_TTM"].abs()
    )

    df["FCF_to_NI"] = safe_div(
        df["FCF_TTM"],
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

    df["GrossMargin"] = safe_div(
        df["GrossProfit_TTM"],
        df["Revenue_TTM"]
    )

    df["FCFMargin"] = safe_div(
        df["FCF_TTM"],
        df["Revenue_TTM"]
    )

    df["BuybackYieldProxy"] = safe_div(
        df["Buyback_TTM"].abs(),
        df["Revenue_TTM"]
    )

    scores = []
    flags = []

    for _, row in df.iterrows():

        score = 0
        flag_list = []

        if pd.notna(row["AccrualRatio"]):

            if row["AccrualRatio"] > 0.10:
                score += 25
                flag_list.append(
                    "Accrual distortion severe"
                )

            elif row["AccrualRatio"] > 0.05:
                score += 15
                flag_list.append(
                    "Accrual distortion moderate"
                )

        if (
            pd.notna(row["CFO_to_NI"])
            and row["NetIncome_TTM"] > 0
        ):

            if row["CFO_to_NI"] < 0.80:
                score += 20
                flag_list.append(
                    "Weak CFO conversion"
                )

            elif row["CFO_to_NI"] < 1.00:
                score += 10
                flag_list.append(
                    "CFO below NI"
                )

        if pd.notna(row["SBC_to_Revenue"]):

            if row["SBC_to_Revenue"] > 0.15:
                score += 20
                flag_list.append(
                    "High SBC burden"
                )

            elif row["SBC_to_Revenue"] > 0.08:
                score += 10
                flag_list.append(
                    "Moderate SBC burden"
                )

        if pd.notna(row["DSO"]):

            if row["DSO"] > 90:
                score += 15
                flag_list.append(
                    "High DSO"
                )

            elif row["DSO"] > 60:
                score += 10
                flag_list.append(
                    "Moderate DSO"
                )

        if pd.notna(row["InventoryDays"]):

            if row["InventoryDays"] > 120:
                score += 15
                flag_list.append(
                    "Inventory buildup"
                )

            elif row["InventoryDays"] > 90:
                score += 10
                flag_list.append(
                    "Moderate inventory buildup"
                )

        if (
            pd.notna(row["ROIC_WACC_Spread"])
            and row["ROIC_WACC_Spread"] < 0
        ):
            score += 15
            flag_list.append(
                "ROIC below WACC"
            )

        scores.append(
            min(score, 100)
        )

        flags.append(
            "; ".join(flag_list)
            if flag_list
            else "No major red flags"
        )

    df["ForensicRiskScore"] = scores
    df["QualityScore"] = (
        100
        -
        df["ForensicRiskScore"]
    )
    df["Flags"] = flags

    df = (
        df
        .sort_values("date")
        .drop_duplicates(
            subset="date",
            keep="last"
        )
        .reset_index(drop=True)
    )

    valid = df.dropna(
        subset=[
            "ROIC_TTM",
            "AccrualRatio"
        ],
        how="all"
    )

    if valid.empty:
        latest_row = df.iloc[-1]
    else:
        latest_row = valid.iloc[-1]

    latest = latest_row.to_dict()

    latest["Ticker"] = ticker
    latest["Company"] = company
    latest["CIK"] = cik

    latest["LatestPeriodEnd"] = latest.get(
        "date"
    )

    latest["LatestForm"] = latest.get(
        "Revenue_form",
        None
    )

    latest["LatestFiled"] = latest.get(
        "Revenue_filed",
        None
    )

    latest["Grade"] = forensic_grade(
        latest.get(
            "ForensicRiskScore",
            np.nan
        )
    )

    latest["Regime"] = regime_label(
        latest
    )

    return {
        "ticker": ticker,
        "company": company,
        "cik": cik,
        "df": df,
        "latest": latest,
        "used_tags": used_tags
    }
