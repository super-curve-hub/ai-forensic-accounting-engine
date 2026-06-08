import pandas as pd

from engine import run_forensic_engine


DEFAULT_UNIVERSE = [
    "NVDA",
    "AVGO",
    "AMD",
    "MU",
    "MRVL",
    "AAPL",
    "MSFT",
    "META",
    "GOOG",
    "AMZN",
    "TSLA",
    "AUR",
    "PLTR",
    "SNOW",
    "CRWD"
]

DEFAULT_WATCHLIST = [
    "NVDA",
    "AVGO",
    "AAPL",
    "MSFT",
    "META",
    "AUR"
]


def latest_row_for_table(result):

    latest = result["latest"]

    economic_ratio = None

    try:

        nopat = latest.get("NOPAT_TTM")
        economic = latest.get("EconomicEarnings_TTM")

        if (
            nopat is not None
            and economic is not None
            and nopat != 0
        ):
            economic_ratio = economic / nopat

    except Exception:
        economic_ratio = None

    return {
        "Ticker": latest.get("Ticker"),
        "Company": latest.get("Company"),
        "Grade": latest.get("Grade"),
        "Regime": latest.get("Regime"),
        "ROIC": latest.get("ROIC_TTM"),
        "ROIC-WACC": latest.get("ROIC_WACC_Spread"),
        "Accrual": latest.get("AccrualRatio"),
        "CFO/NI": latest.get("CFO_to_NI"),
        "FCF/NI": latest.get("FCF_to_NI"),
        "EconomicRatio": economic_ratio,
        "SBC/Revenue": latest.get("SBC_to_Revenue"),
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


def screen_quality_compounders(df):

    return apply_screen(
        df=df,
        roic_min_pct=20,
        risk_max=20,
        accrual_max_pct=0,
        require_cfo_gt_1=True,
        require_positive_spread=True
    )


def screen_high_sbc(
    df,
    threshold=0.10
):

    if df.empty:
        return df

    return df[
        df["SBC/Revenue"].fillna(0)
        > threshold
    ]


def screen_value_destruction(df):

    if df.empty:
        return df

    return df[
        df["ROIC-WACC"].fillna(999)
        < 0
    ]


def rank_companies(df):

    if df.empty:
        return df

    ranked = df.copy()

    ranked["RankScore"] = (
        ranked["Quality"].fillna(0)
        + ranked["ROIC"].fillna(0) * 100
        - ranked["Risk"].fillna(0)
    )

    ranked = ranked.sort_values(
        "RankScore",
        ascending=False
    )

    return ranked.reset_index(drop=True)
