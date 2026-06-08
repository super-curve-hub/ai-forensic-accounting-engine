import pandas as pd

from engine import run_forensic_engine

DEFAULT_UNIVERSE = [
    "NVDA", "AVGO", "AMD", "MU", "MRVL",
    "AAPL", "MSFT", "META", "GOOG", "AMZN",
    "TSLA", "AUR", "PLTR", "SNOW", "CRWD"
]

DEFAULT_WATCHLIST = ["NVDA", "AVGO", "AAPL", "MSFT", "META", "AUR"]

def latest_row_for_table(result):
    latest = result["latest"]
    return {
        "Ticker": latest.get("Ticker"),
        "Company": latest.get("Company"),
        "Grade": latest.get("Grade"),
        "Regime": latest.get("Regime"),
        "ROIC": latest.get("ROIC_TTM"),
        "ROIC-WACC": latest.get("ROIC_WACC_Spread"),
        "Accrual": latest.get("AccrualRatio"),
        "CFO/NI": latest.get("CFO_to_NI"),
        "SBC/Revenue": latest.get("SBC_to_Revenue"),
        "DSO": latest.get("DSO"),
        "InventoryDays": latest.get("InventoryDays"),
        "Risk": latest.get("ForensicRiskScore"),
        "Quality": latest.get("QualityScore"),
        "Flags": latest.get("Flags"),
    }

def run_ticker_list(tickers, wacc):
    rows = []
    errors = []

    for t in tickers:
        try:
            result = run_forensic_engine(t, wacc=wacc)
            rows.append(latest_row_for_table(result))
        except Exception as e:
            errors.append({"Ticker": t, "Error": str(e)})

    return pd.DataFrame(rows), pd.DataFrame(errors)

def apply_screen(df, roic_min_pct, risk_max, accrual_max_pct, require_cfo_gt_1=False):
    if df.empty:
        return df

    screen = df[
        (df["ROIC"].fillna(-999) >= roic_min_pct / 100) &
        (df["Risk"].fillna(999) <= risk_max) &
        (df["Accrual"].fillna(999) <= accrual_max_pct / 100)
    ].copy()

    if require_cfo_gt_1:
        screen = screen[screen["CFO/NI"].fillna(-999) > 1]

    return screen
