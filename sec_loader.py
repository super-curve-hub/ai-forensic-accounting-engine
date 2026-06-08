import pandas as pd
import requests
import streamlit as st

USER_AGENT = "AI Forensic Accounting Engine/3.0 contact: i.love.melonpan@gmail.com"
HEADERS = {"User-Agent": USER_AGENT}

TAG_MAP = {
    "Revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues"
    ],
    "COGS": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfGoodsSoldExcludingDepreciationDepletionAndAmortization",
        "CostOfRevenueExcludingDepreciationAndAmortization"
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
    "Assets": ["Assets"],
    "Liabilities": ["Liabilities"],
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
}

@st.cache_data(ttl=3600, show_spinner=False)
def get_sec_json(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"SEC request failed: {response.status_code}")
    return response.json()

@st.cache_data(ttl=86400, show_spinner=False)
def ticker_map():
    data = get_sec_json("https://www.sec.gov/files/company_tickers.json")
    df = pd.DataFrame(data).T
    df["ticker"] = df["ticker"].str.upper()
    return df

def ticker_to_cik(ticker):
    ticker = ticker.upper().strip()
    df = ticker_map()
    row = df[df["ticker"] == ticker]
    if row.empty:
        raise ValueError(f"Ticker not found: {ticker}")
    cik = str(row.iloc[0]["cik_str"]).zfill(10)
    company = row.iloc[0]["title"]
    return cik, company

@st.cache_data(ttl=3600, show_spinner=False)
def load_companyfacts(cik):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    data = get_sec_json(url)
    facts = data.get("facts", {}).get("us-gaap", {})
    if not facts:
        raise RuntimeError("No us-gaap facts found")
    return facts

def get_fact(facts, tag):
    if tag not in facts:
        return pd.DataFrame()

    frames = []
    for unit, values in facts[tag].get("units", {}).items():
        temp = pd.DataFrame(values)
        if temp.empty:
            continue
        temp["tag"] = tag
        temp["unit"] = unit
        frames.append(temp)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)

def series_for_tag(facts, tag):
    raw = get_fact(facts, tag)

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

    temp = (
        temp.sort_values(["date", "filed"])
        .drop_duplicates("date", keep="last")
    )

    return temp[["date", "val"]].rename(columns={"val": tag})

def resolve_metric(facts, metric, tags):
    best = None
    best_tag = None
    best_count = -1

    for tag in tags:
        s = series_for_tag(facts, tag)
        if s.empty:
            continue
        count = s[tag].notna().sum()
        if count > best_count:
            best = s
            best_tag = tag
            best_count = count

    if best is None:
        return pd.DataFrame(columns=["date", metric]), None

    return best.rename(columns={best_tag: metric}), best_tag

def build_statement_dataframe(facts):
    master = None
    used_tags = {}

    for metric, tags in TAG_MAP.items():
        s, tag = resolve_metric(facts, metric, tags)
        used_tags[metric] = tag if tag else "NOT FOUND"

        if s.empty:
            continue

        master = s if master is None else master.merge(s, on="date", how="outer")

    if master is None or master.empty:
        raise RuntimeError("No usable financial facts found")

    df = master.sort_values("date").reset_index(drop=True)

    for col in df.columns:
        if col != "date":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    required = list(TAG_MAP.keys())
    for col in required:
        if col not in df.columns:
            df[col] = pd.NA

    return df, used_tags
