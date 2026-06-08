import pandas as pd
import numpy as np

def safe_div(a, b):
    out = a / b
    if isinstance(out, pd.Series):
        return out.replace([np.inf, -np.inf], np.nan)
    try:
        return np.nan if np.isinf(out) else out
    except Exception:
        return out

def pct_fmt(x, digits=1):
    return "NA" if pd.isna(x) else f"{x * 100:.{digits}f}%"

def ratio_fmt(x, digits=2):
    return "NA" if pd.isna(x) else f"{x:.{digits}f}"

def num_fmt(x, digits=1):
    return "NA" if pd.isna(x) else f"{x:.{digits}f}"

def money_fmt(x):
    if pd.isna(x):
        return "NA"
    ax = abs(x)
    if ax >= 1e12:
        return f"${x/1e12:.2f}T"
    if ax >= 1e9:
        return f"${x/1e9:.1f}B"
    if ax >= 1e6:
        return f"${x/1e6:.1f}M"
    return f"${x:,.0f}"

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

def grade_emoji(grade):
    return {
        "A": "🟢",
        "B": "🔵",
        "C": "🟡",
        "D": "🟠",
        "F": "🔴",
        "NA": "⚪"
    }.get(grade, "⚪")

def grade_class(grade):
    return {
        "A": "grade-a",
        "B": "grade-b",
        "C": "grade-c",
        "D": "grade-d",
        "F": "grade-f",
    }.get(grade, "grade-c")

def regime_label(latest):
    roic = latest.get("ROIC_TTM", np.nan)
    spread = latest.get("ROIC_WACC_Spread", np.nan)
    accrual = latest.get("AccrualRatio", np.nan)
    cfo = latest.get("CFO_to_NI", np.nan)
    risk = latest.get("ForensicRiskScore", np.nan)
    sbc = latest.get("SBC_to_Revenue", np.nan)

    if pd.notna(spread) and pd.notna(accrual) and pd.notna(cfo) and pd.notna(risk):
        if spread > 0 and accrual < 0 and cfo > 1 and risk <= 20:
            return "Quality Compounder"
    if pd.notna(spread) and spread < 0:
        return "Value Destruction"
    if pd.notna(sbc) and sbc > 0.15:
        return "High SBC Growth"
    if pd.notna(accrual) and accrual > 0.10:
        return "Accrual Stress"
    if pd.notna(roic) and roic > 0.20 and pd.notna(risk) and risk <= 40:
        return "High ROIC / Monitor"
    return "Neutral / Inconclusive"
