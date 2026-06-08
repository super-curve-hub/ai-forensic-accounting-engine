import streamlit as st
from utils import pct_fmt, ratio_fmt, num_fmt, grade_emoji, grade_class

def inject_card_css():
    st.markdown(
        """
        <style>
        .main-title {
            font-size: 2.1rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-bottom: 0.1rem;
        }
        .sub-title {
            color: #666;
            font-size: 0.95rem;
            margin-bottom: 1.2rem;
        }
        .hero-card {
            border-radius: 24px;
            padding: 24px;
            margin: 12px 0 20px 0;
            background: linear-gradient(135deg, rgba(40,40,52,0.95), rgba(15,15,22,0.95));
            color: white;
            border: 1px solid rgba(255,255,255,0.10);
        }
        .hero-name {
            font-size: 1.75rem;
            font-weight: 800;
            margin-bottom: 6px;
        }
        .hero-sub {
            color: rgba(255,255,255,0.72);
            font-size: 0.95rem;
            margin-bottom: 14px;
        }
        .metric-card {
            border: 1px solid rgba(49, 51, 63, 0.15);
            border-radius: 18px;
            padding: 18px 18px;
            background: rgba(255,255,255,0.65);
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            margin-bottom: 12px;
        }
        .metric-label {
            font-size: 0.78rem;
            color: #666;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 1.55rem;
            font-weight: 800;
            color: #111;
        }
        .small-note {
            font-size: 0.78rem;
            color: #777;
        }
        .grade-a {
            background: rgba(32, 201, 151, 0.12);
            border: 1px solid rgba(32, 201, 151, 0.35);
            color: #087f5b;
        }
        .grade-b {
            background: rgba(116, 192, 252, 0.12);
            border: 1px solid rgba(116, 192, 252, 0.35);
            color: #1864ab;
        }
        .grade-c {
            background: rgba(255, 212, 59, 0.16);
            border: 1px solid rgba(255, 212, 59, 0.45);
            color: #8d6b00;
        }
        .grade-d {
            background: rgba(255, 146, 43, 0.14);
            border: 1px solid rgba(255, 146, 43, 0.45);
            color: #b35c00;
        }
        .grade-f {
            background: rgba(250, 82, 82, 0.12);
            border: 1px solid rgba(250, 82, 82, 0.45);
            color: #c92a2a;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def page_title():
    st.markdown('<div class="main-title">AI Forensic Accounting Engine</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">SEC 10-K / 10-Q based accounting quality, ROIC, accrual and risk platform</div>',
        unsafe_allow_html=True
    )

def hero_card(latest, wacc_pct):
    company = latest.get("Company", "NA")
    ticker = latest.get("Ticker", "NA")
    grade = latest.get("Grade", "NA")
    regime = latest.get("Regime", "NA")
    risk = ratio_fmt(latest.get("ForensicRiskScore"), 0)
    roic = pct_fmt(latest.get("ROIC_TTM"))
    spread = pct_fmt(latest.get("ROIC_WACC_Spread"))
    emoji = grade_emoji(grade)

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-name">{company}</div>
            <div class="hero-sub">{ticker} | WACC {wacc_pct:.1f}%</div>
            <div style="font-size:1.2rem;font-weight:800;">{emoji} Grade {grade} — {regime}</div>
            <div style="margin-top:14px;display:flex;gap:22px;flex-wrap:wrap;">
                <div>ROIC<br><b style="font-size:1.35rem;">{roic}</b></div>
                <div>ROIC-WACC<br><b style="font-size:1.35rem;">{spread}</b></div>
                <div>Risk<br><b style="font-size:1.35rem;">{risk}</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def metric_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="small-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def metric_cards(latest):
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("ROIC", pct_fmt(latest.get("ROIC_TTM")), "Return on invested capital")
    with c2:
        metric_card("ROIC-WACC", pct_fmt(latest.get("ROIC_WACC_Spread")), "Economic spread")
    with c3:
        metric_card("Risk", ratio_fmt(latest.get("ForensicRiskScore"), 0), "Lower is better")

    c4, c5, c6 = st.columns(3)
    with c4:
        metric_card("Accrual", pct_fmt(latest.get("AccrualRatio")), "Negative is usually better")
    with c5:
        metric_card("CFO / NI", ratio_fmt(latest.get("CFO_to_NI")), "Cash conversion")
    with c6:
        metric_card("SBC / Revenue", pct_fmt(latest.get("SBC_to_Revenue")), "Dilution pressure")

def stock_card(row):
    ticker = row.get("Ticker", "NA")
    company = row.get("Company", "")
    grade = row.get("Grade", "NA")
    regime = row.get("Regime", "NA")
    emoji = grade_emoji(grade)

    with st.container(border=True):
        st.markdown(f"### {emoji} {ticker} — Grade {grade}")
        st.caption(company)
        st.caption(regime)

        c1, c2, c3 = st.columns(3)
        c1.metric("ROIC", pct_fmt(row.get("ROIC")))
        c2.metric("Risk", num_fmt(row.get("Risk"), 0))
        c3.metric("Accrual", pct_fmt(row.get("Accrual")))

        c4, c5, c6 = st.columns(3)
        c4.metric("CFO / NI", ratio_fmt(row.get("CFO/NI")))
        c5.metric("SBC", pct_fmt(row.get("SBC/Revenue")))
        c6.metric("DSO", num_fmt(row.get("DSO")))
