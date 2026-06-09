import pandas as pd
import numpy as np

from engine import run_forensic_engine


DEFAULT_UNIVERSE = [
    "COHR",
    "LITE",
    "NVDA",
    "AVGO",
    "ANET",
    "MRVL",
    "AMD",
    "MU",
    "TSM",
    "MSFT",
    "AMZN",
    "META"
]


DEFAULT_WATCHLIST = [
    "COHR",
    "LITE",
    "AVGO",
    "ANET",
    "MRVL",
    "NVDA"
]


COMPARE_PRESETS = {
    "Photonics": [
        "COHR",
        "LITE",
        "AVGO",
        "ANET",
        "MRVL",
        "NVDA"
    ],

    "AI Infrastructure": [
        "NVDA",
        "AVGO",
        "AMD",
        "MU",
        "ANET",
        "MRVL"
    ],

    "Magnificent 7": [
        "AAPL",
        "MSFT",
        "AMZN",
        "META",
        "GOOG",
        "NVDA",
        "TSLA"
    ],

    "Semiconductors": [
        "NVDA",
        "AMD",
        "AVGO",
        "MU",
        "TSM",
        "MRVL"
    ]
}


def latest_row_for_table(result):

    latest = result["latest"]

    nopat = latest.get("NOPAT_TTM")
    economic = latest.get("EconomicEarnings_TTM")

    economic_ratio = np.nan

    if (
        nopat is not None
        and economic is not None
        and nopat != 0
    ):
        economic_ratio = economic / nopat

    return {
        "Ticker": latest.get("Ticker"),
        "Company": latest.get("Company"),
        "Grade": latest.get("Grade"),
        "Regime": latest.get("Regime"),

        "ROIC": latest.get("ROIC_TTM"),
        "ROIC-WACC": latest.get("ROIC_WACC_Spread"),

        "EconomicEarnings": latest.get("EconomicEarnings_TTM"),
        "EconomicRatio": economic_ratio,

        "Accrual": latest.get("AccrualRatio"),
        "CFO/NI": latest.get("CFO_to_NI"),
        "FCF/NI": latest.get("FCF_to_NI"),

        "SBC/Revenue": latest.get("SBC_to_Revenue"),

        "GrossMargin": latest.get("GrossMargin"),
        "FCFMargin": latest.get("FCFMargin"),
        "BuybackYield": latest.get("BuybackYieldProxy"),

        "DSO": latest.get("DSO"),
        "InventoryDays": latest.get("InventoryDays"),

        "Risk": latest.get("ForensicRiskScore"),
        "Quality": latest.get("QualityScore"),

        "Flags": latest.get("Flags")
    }


def run_ticker_list(tickers, wacc):

    rows = []
    errors = []

    for ticker in tickers:

        try:
            result = run_forensic_engine(
                ticker,
                wacc=wacc
            )

            rows.append(
                latest_row_for_table(result)
            )

        except Exception as e:
            errors.append(
                {
                    "Ticker": ticker,
                    "Error": str(e)
                }
            )

    return (
        pd.DataFrame(rows),
        pd.DataFrame(errors)
    )


def apply_screen(
    df,
    roic_min_pct,
    risk_max,
    accrual_max_pct,
    require_cfo_gt_1=False,
    require_positive_spread=False
):

    if df.empty:
        return df

    screen = df.copy()

    screen = screen[
        screen["ROIC"].fillna(-999)
        >= roic_min_pct / 100
    ]

    screen = screen[
        screen["Risk"].fillna(999)
        <= risk_max
    ]

    screen = screen[
        screen["Accrual"].fillna(999)
        <= accrual_max_pct / 100
    ]

    if require_cfo_gt_1:
        screen = screen[
            screen["CFO/NI"].fillna(-999)
            > 1
        ]

    if require_positive_spread:
        screen = screen[
            screen["ROIC-WACC"].fillna(-999)
            > 0
        ]

    return screen


def rank_companies(df):

    if df.empty:
        return df

    ranked = df.copy()

    ranked["ROICScore"] = (
        ranked["ROIC"]
        .fillna(0)
        * 100
    )

    ranked["MarginScore"] = (
        ranked["GrossMargin"]
        .fillna(0)
        * 50
        +
        ranked["FCFMargin"]
        .fillna(0)
        * 50
    )

    ranked["CashScore"] = (
        ranked["CFO/NI"]
        .fillna(0)
        * 25
    )

    ranked["CapitalAllocationScore"] = (
        ranked["ROIC-WACC"]
        .fillna(0)
        * 100
        +
        ranked["BuybackYield"]
        .fillna(0)
        * 300
        -
        ranked["SBC/Revenue"]
        .fillna(0)
        * 300
    )

    ranked["RiskScore"] = (
        100
        -
        ranked["Risk"]
        .fillna(100)
    )

    ranked["EconomicScore"] = (
        ranked["ROICScore"]
        +
        ranked["MarginScore"]
        +
        ranked["CashScore"]
        +
        ranked["CapitalAllocationScore"]
        +
        ranked["RiskScore"]
    )

    ranked = ranked.sort_values(
        "EconomicScore",
        ascending=False
    )

    return ranked.reset_index(
        drop=True
    )
