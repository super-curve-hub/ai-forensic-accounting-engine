import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px

st.set_page_config(page_title="AI Forensic Accounting Engine", layout="wide")

st.markdown("""
<style>
.main-title{font-size:2.1rem;font-weight:800;letter-spacing:-.03em;margin-bottom:.1rem}.sub-title{color:#666;font-size:.95rem;margin-bottom:1.2rem}.metric-card{border:1px solid rgba(49,51,63,.15);border-radius:18px;padding:18px;background:rgba(255,255,255,.65);box-shadow:0 1px 3px rgba(0,0,0,.04);margin-bottom:12px}.metric-label{font-size:.78rem;color:#666;margin-bottom:8px}.metric-value{font-size:1.55rem;font-weight:800;color:#111}.small-note{font-size:.78rem;color:#777}.grade-box{border-radius:18px;padding:18px;margin-top:8px;margin-bottom:16px;font-weight:700}.grade-a{background:rgba(32,201,151,.12);border:1px solid rgba(32,201,151,.35);color:#087f5b}.grade-b{background:rgba(116,192,252,.12);border:1px solid rgba(116,192,252,.35);color:#1864ab}.grade-c{background:rgba(255,212,59,.16);border:1px solid rgba(255,212,59,.45);color:#8d6b00}.grade-d{background:rgba(255,146,43,.14);border:1px solid rgba(255,146,43,.45);color:#b35c00}.grade-f{background:rgba(250,82,82,.12);border:1px solid rgba(250,82,82,.45);color:#c92a2a}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">AI Forensic Accounting Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">SEC 10-K / 10-Q based accounting quality, ROIC, accrual and risk dashboard</div>', unsafe_allow_html=True)

USER_AGENT = "your_email@example.com"
headers = {"User-Agent": USER_AGENT}
DEFAULT_UNIVERSE = ["NVDA","AVGO","AMD","MU","MRVL","AAPL","MSFT","META","GOOG","AMZN","TSLA","AUR","PLTR","SNOW","CRWD"]
DEFAULT_WATCHLIST = ["NVDA","AVGO","AAPL","MSFT","META","AUR"]

def safe_div(a,b):
    out=a/b
    if isinstance(out,pd.Series):
        out=out.replace([np.inf,-np.inf],np.nan)
    else:
        try:
            if np.isinf(out): out=np.nan
        except Exception: pass
    return out

def pct_fmt(x,digits=1): return "NA" if pd.isna(x) else f"{x*100:.{digits}f}%"
def ratio_fmt(x,digits=2): return "NA" if pd.isna(x) else f"{x:.{digits}f}"
def num_fmt(x,digits=1): return "NA" if pd.isna(x) else f"{x:.{digits}f}"
def money_fmt(x):
    if pd.isna(x): return "NA"
    ax=abs(x)
    if ax>=1e12: return f"${x/1e12:.2f}T"
    if ax>=1e9: return f"${x/1e9:.1f}B"
    if ax>=1e6: return f"${x/1e6:.1f}M"
    return f"${x:,.0f}"

def forensic_grade(score):
    if pd.isna(score): return "NA"
    if score<=20: return "A"
    if score<=40: return "B"
    if score<=60: return "C"
    if score<=80: return "D"
    return "F"

def grade_class(grade): return {"A":"grade-a","B":"grade-b","C":"grade-c","D":"grade-d","F":"grade-f"}.get(grade,"grade-c")

def regime_label(latest):
    roic=latest.get("ROIC_TTM",np.nan); spread=latest.get("ROIC_WACC_Spread",np.nan); accrual=latest.get("AccrualRatio",np.nan); cfo=latest.get("CFO_to_NI",np.nan); risk=latest.get("ForensicRiskScore",np.nan); sbc=latest.get("SBC_to_Revenue",np.nan)
    if pd.notna(spread) and pd.notna(accrual) and pd.notna(cfo) and pd.notna(risk) and spread>0 and accrual<0 and cfo>1 and risk<=20: return "Quality Compounder"
    if pd.notna(spread) and spread<0: return "Value Destruction"
    if pd.notna(sbc) and sbc>0.15: return "High SBC Growth"
    if pd.notna(accrual) and accrual>0.10: return "Accrual Stress"
    if pd.notna(roic) and roic>0.20 and pd.notna(risk) and risk<=40: return "High ROIC / Monitor"
    return "Neutral / Inconclusive"

def metric_card(label,value,note=""):
    st.markdown(f"""<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="small-note">{note}</div></div>""", unsafe_allow_html=True)

@st.cache_data(ttl=3600, show_spinner=False)
def get_sec_json(url):
    r=requests.get(url,headers=headers,timeout=30)
    if r.status_code!=200: raise RuntimeError(f"SEC request failed: {r.status_code}")
    return r.json()

@st.cache_data(ttl=86400, show_spinner=False)
def ticker_map():
    tickers=get_sec_json("https://www.sec.gov/files/company_tickers.json")
    df=pd.DataFrame(tickers).T; df["ticker"]=df["ticker"].str.upper(); return df

def ticker_to_cik(ticker):
    t=ticker.upper().strip(); df=ticker_map(); row=df[df["ticker"]==t]
    if row.empty: raise ValueError(f"Ticker not found: {t}")
    return str(row.iloc[0]["cik_str"]).zfill(10), row.iloc[0]["title"]

@st.cache_data(ttl=3600, show_spinner=False)
def run_forensic_engine(ticker,wacc=0.10):
    ticker=ticker.upper().strip(); cik, company=ticker_to_cik(ticker)
    data=get_sec_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
    facts=data.get("facts",{}).get("us-gaap",{})
    if not facts: raise RuntimeError("No us-gaap facts found")
    def get_fact(tag):
        if tag not in facts: return pd.DataFrame()
        frames=[]
        for unit, vals in facts[tag].get("units",{}).items():
            tmp=pd.DataFrame(vals)
            if tmp.empty: continue
            tmp["tag"]=tag; tmp["unit"]=unit; frames.append(tmp)
        return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()
    def series_for_tag(tag):
        raw=get_fact(tag)
        if raw.empty: return pd.DataFrame(columns=["date",tag])
        req={"form","unit","end","val"}
        if not req.issubset(set(raw.columns)): return pd.DataFrame(columns=["date",tag])
        tmp=raw[(raw["form"].isin(["10-Q","10-Q/A","10-K","10-K/A"])) & (raw["unit"]=="USD")].copy()
        if tmp.empty: return pd.DataFrame(columns=["date",tag])
        tmp["date"]=pd.to_datetime(tmp["end"],errors="coerce"); tmp["filed"]=pd.to_datetime(tmp.get("filed"),errors="coerce")
        tmp=tmp.dropna(subset=["date"]).sort_values(["date","filed"]).drop_duplicates("date",keep="last")
        return tmp[["date","val"]].rename(columns={"val":tag})
    def resolve_metric(metric,candidates):
        best=None; best_tag=None; best_count=-1
        for tag in candidates:
            s=series_for_tag(tag)
            if s.empty: continue
            count=s[tag].notna().sum()
            if count>best_count: best=s; best_tag=tag; best_count=count
        if best is None: return pd.DataFrame(columns=["date",metric]), None
        return best.rename(columns={best_tag:metric}), best_tag
    TAG_MAP={
        "Revenue":["RevenueFromContractWithCustomerExcludingAssessedTax","SalesRevenueNet","Revenues"],
        "OperatingIncome":["OperatingIncomeLoss","IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
        "PretaxIncome":["IncomeBeforeTaxExpenseBenefit","IncomeBeforeIncomeTaxes","IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
        "IncomeTax":["IncomeTaxExpenseBenefit","CurrentIncomeTaxExpenseBenefit","IncomeTaxesPaidNet"],
        "NetIncome":["NetIncomeLoss","ProfitLoss"],
        "CFO":["NetCashProvidedByUsedInOperatingActivities","NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
        "Capex":["PaymentsToAcquirePropertyPlantAndEquipment","PaymentsToAcquireProductiveAssets","CapitalExpendituresIncurredButNotYetPaid"],
        "Assets":["Assets"],"Liabilities":["Liabilities"],"Equity":["StockholdersEquity","StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
        "Cash":["CashAndCashEquivalentsAtCarryingValue","CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
        "Receivables":["AccountsReceivableNetCurrent","AccountsReceivableNet","ReceivablesNetCurrent","ReceivablesNet"],
        "Inventory":["InventoryNet","InventoryFinishedGoodsNetOfReserves","InventoryRawMaterialsAndPurchasedPartsNetOfReserves"],
        "SBC":["ShareBasedCompensation","ShareBasedCompensationArrangementByShareBasedPaymentAwardExpense"],
        "OperatingLeaseLiability":["OperatingLeaseLiability","OperatingLeaseLiabilityCurrent","OperatingLeaseLiabilityNoncurrent"],
        "DeferredRevenue":["ContractWithCustomerLiabilityCurrent","DeferredRevenueCurrent","DeferredRevenueAndCreditsCurrent"]}
    master=None; used_tags={}
    for metric,candidates in TAG_MAP.items():
        s,tag=resolve_metric(metric,candidates); used_tags[metric]=tag if tag else "NOT FOUND"
        if s.empty: continue
        master=s if master is None else master.merge(s,on="date",how="outer")
    if master is None or master.empty: raise RuntimeError("No usable financial facts found")
    df=master.sort_values("date").reset_index(drop=True)
    for col in df.columns:
        if col!="date": df[col]=pd.to_numeric(df[col],errors="coerce")
    required=["Revenue","OperatingIncome","PretaxIncome","IncomeTax","NetIncome","CFO","Capex","Assets","Liabilities","Equity","Cash","Receivables","Inventory","SBC","OperatingLeaseLiability","DeferredRevenue"]
    for col in required:
        if col not in df.columns: df[col]=np.nan
    for col in ["Cash","SBC","OperatingLeaseLiability","DeferredRevenue"]: df[col]=df[col].fillna(0)
    flows=["Revenue","OperatingIncome","PretaxIncome","IncomeTax","NetIncome","CFO","Capex","SBC"]
    for col in flows: df[f"{col}_TTM"]=df[col].rolling(4,min_periods=4).sum()
    df["TaxRate"]=safe_div(df["IncomeTax_TTM"],df["PretaxIncome_TTM"]).replace([np.inf,-np.inf],np.nan).clip(0,0.35).fillna(0.21)
    df["NOPAT_TTM"]=df["OperatingIncome_TTM"]*(1-df["TaxRate"])
    df["NOPAT_TTM"]=df["NOPAT_TTM"].fillna(df["PretaxIncome_TTM"]*(1-df["TaxRate"]))
    df["InvestedCapital"]=df["Equity"].fillna(0)+df["Liabilities"].fillna(0)-df["Cash"].fillna(0)+df["OperatingLeaseLiability"].fillna(0)
    df["InvestedCapital"]=df["InvestedCapital"].replace(0,np.nan); df["AvgIC"]=df["InvestedCapital"].rolling(2,min_periods=2).mean()
    df["ROIC_TTM"]=safe_div(df["NOPAT_TTM"],df["AvgIC"]); df["ROIC_WACC_Spread"]=df["ROIC_TTM"]-wacc; df["EconomicEarnings_TTM"]=df["NOPAT_TTM"]-wacc*df["AvgIC"]
    df["Accruals_TTM"]=df["NetIncome_TTM"]-df["CFO_TTM"]; df["AvgAssets"]=df["Assets"].rolling(2,min_periods=2).mean(); df["AccrualRatio"]=safe_div(df["Accruals_TTM"],df["AvgAssets"])
    df["CFO_to_NI"]=safe_div(df["CFO_TTM"],df["NetIncome_TTM"]); df["FCF_TTM"]=df["CFO_TTM"]-df["Capex_TTM"].abs(); df["FCF_to_NI"]=safe_div(df["FCF_TTM"],df["NetIncome_TTM"])
    df["SBC_to_Revenue"]=safe_div(df["SBC_TTM"],df["Revenue_TTM"]); df["DSO"]=safe_div(df["Receivables"],df["Revenue_TTM"]/365); df["InventoryDays"]=safe_div(df["Inventory"],df["Revenue_TTM"]/365)
    scores=[]; flags=[]
    for _,row in df.iterrows():
        score=0; f=[]
        if pd.notna(row["AccrualRatio"]):
            if row["AccrualRatio"]>0.10: score+=25; f.append("Accrual distortion severe")
            elif row["AccrualRatio"]>0.05: score+=15; f.append("Accrual distortion moderate")
        if pd.notna(row["CFO_to_NI"]) and row["NetIncome_TTM"]>0:
            if row["CFO_to_NI"]<0.80: score+=20; f.append("Weak CFO conversion")
            elif row["CFO_to_NI"]<1.00: score+=10; f.append("CFO below NI")
        if pd.notna(row["SBC_to_Revenue"]):
            if row["SBC_to_Revenue"]>0.15: score+=20; f.append("High SBC burden")
            elif row["SBC_to_Revenue"]>0.08: score+=10; f.append("Moderate SBC burden")
        if pd.notna(row["DSO"]):
            if row["DSO"]>90: score+=15; f.append("High DSO")
            elif row["DSO"]>60: score+=10; f.append("Moderate DSO")
        if pd.notna(row["InventoryDays"]):
            if row["InventoryDays"]>120: score+=15; f.append("Inventory buildup")
            elif row["InventoryDays"]>90: score+=10; f.append("Moderate inventory buildup")
        if pd.notna(row["ROIC_WACC_Spread"]) and row["ROIC_WACC_Spread"]<0: score+=15; f.append("ROIC below WACC")
        scores.append(min(score,100)); flags.append("; ".join(f) if f else "No major red flags")
    df["ForensicRiskScore"]=scores; df["QualityScore"]=100-df["ForensicRiskScore"]; df["Flags"]=flags
    valid=df.dropna(subset=["ROIC_TTM","AccrualRatio"],how="all"); latest=(df.iloc[-1] if valid.empty else valid.iloc[-1]).to_dict()
    latest.update({"Ticker":ticker,"Company":company,"CIK":cik,"Grade":forensic_grade(latest.get("ForensicRiskScore",np.nan))})
    latest["Regime"]=regime_label(latest)
    return {"ticker":ticker,"company":company,"cik":cik,"df":df,"latest":latest,"used_tags":used_tags}

def render_kpi_cards(latest):
    c1,c2=st.columns(2)
    with c1: metric_card("ROIC",pct_fmt(latest.get("ROIC_TTM")),"Return on invested capital")
    with c2: metric_card("Forensic Risk",ratio_fmt(latest.get("ForensicRiskScore"),0),"Lower is better")
    c3,c4=st.columns(2)
    with c3: metric_card("Accrual Ratio",pct_fmt(latest.get("AccrualRatio")),"Negative is usually better")
    with c4: metric_card("CFO / NI",ratio_fmt(latest.get("CFO_to_NI")),"Cash conversion")
    c5,c6=st.columns(2)
    with c5: metric_card("SBC / Revenue",pct_fmt(latest.get("SBC_to_Revenue")),"Dilution pressure")
    with c6: metric_card("DSO",num_fmt(latest.get("DSO")),"NA means receivables tag missing")

def render_grade(latest):
    grade=latest.get("Grade","NA"); regime=latest.get("Regime","Neutral / Inconclusive"); css=grade_class(grade)
    st.markdown(f'<div class="grade-box {css}">Forensic Grade: {grade}<br>Regime: {regime}</div>', unsafe_allow_html=True)
    st.info(f"Flags: {latest.get('Flags','NA')}")

def latest_row_for_table(result):
    l=result["latest"]
    return {"Ticker":l.get("Ticker"),"Company":l.get("Company"),"Grade":l.get("Grade"),"Regime":l.get("Regime"),"ROIC":l.get("ROIC_TTM"),"ROIC-WACC":l.get("ROIC_WACC_Spread"),"Accrual":l.get("AccrualRatio"),"CFO/NI":l.get("CFO_to_NI"),"SBC/Revenue":l.get("SBC_to_Revenue"),"DSO":l.get("DSO"),"InventoryDays":l.get("InventoryDays"),"Risk":l.get("ForensicRiskScore"),"Quality":l.get("QualityScore"),"Flags":l.get("Flags")}

def render_charts(result):
    df=result["df"].copy(); df["ROIC_pct"]=df["ROIC_TTM"]*100; df["Accrual_pct"]=df["AccrualRatio"]*100
    with st.expander("ROIC Trend", expanded=True): st.plotly_chart(px.line(df,x="date",y="ROIC_pct",title="ROIC"),use_container_width=True)
    with st.expander("Accrual Trend"): st.plotly_chart(px.line(df,x="date",y="Accrual_pct",title="Accrual Ratio"),use_container_width=True)
    with st.expander("Forensic Risk Trend"): st.plotly_chart(px.bar(df,x="date",y="ForensicRiskScore",title="Forensic Risk Score"),use_container_width=True)
    with st.expander("DSO / Inventory Days"):
        st.plotly_chart(px.line(df,x="date",y="DSO",title="DSO"),use_container_width=True)
        st.plotly_chart(px.line(df,x="date",y="InventoryDays",title="Inventory Days"),use_container_width=True)

def render_data_tables(result):
    df=result["df"]
    display_cols=["date","Revenue_TTM","NOPAT_TTM","ROIC_TTM","ROIC_WACC_Spread","EconomicEarnings_TTM","AccrualRatio","CFO_to_NI","FCF_to_NI","SBC_to_Revenue","DSO","InventoryDays","ForensicRiskScore","QualityScore","Flags"]
    with st.expander("Raw Financial Data"): st.dataframe(df[[c for c in display_cols if c in df.columns]].tail(20),use_container_width=True)
    with st.expander("Resolved XBRL Tags"): st.dataframe(pd.DataFrame([{"Metric":k,"ResolvedTag":v} for k,v in result["used_tags"].items()]),use_container_width=True)

with st.sidebar:
    st.subheader("Settings")
    wacc_pct=st.number_input("WACC (%)",min_value=0.0,max_value=30.0,value=10.0,step=0.5)
    wacc=wacc_pct/100
    st.caption("Example: 14% = input 14.0")

tab_analysis,tab_watchlist,tab_compare,tab_screening=st.tabs(["Analysis","Watchlist","Compare","Screening"])

with tab_analysis:
    st.subheader("Single Ticker Analysis")
    ci,cb=st.columns([3,1])
    with ci: ticker=st.text_input("Ticker","NVDA",key="analysis_ticker").upper().strip()
    with cb: analyze=st.button("Analyze",key="analysis_button",use_container_width=True)
    if analyze:
        try:
            with st.spinner(f"Analyzing {ticker}..."): result=run_forensic_engine(ticker,wacc=wacc)
            latest=result["latest"]; st.markdown(f"### {latest.get('Company')} ({latest.get('Ticker')})"); st.caption(f"CIK: {latest.get('CIK')} | WACC: {wacc_pct:.1f}%")
            render_grade(latest); render_kpi_cards(latest); render_charts(result); render_data_tables(result)
        except Exception as e:
            st.error("Analysis failed."); st.exception(e)

with tab_watchlist:
    st.subheader("Watchlist")
    selected=st.multiselect("Tickers",DEFAULT_UNIVERSE,default=DEFAULT_WATCHLIST)
    if st.button("Run Watchlist",key="watchlist_button"):
        rows=[]; errors=[]; progress=st.progress(0)
        for i,t in enumerate(selected):
            try:
                with st.spinner(f"Analyzing {t}..."): rows.append(latest_row_for_table(run_forensic_engine(t,wacc=wacc)))
            except Exception as e: errors.append({"Ticker":t,"Error":str(e)})
            progress.progress((i+1)/max(len(selected),1))
        if rows:
            watch_df=pd.DataFrame(rows); st.dataframe(watch_df,use_container_width=True)
            st.plotly_chart(px.bar(watch_df,x="Ticker",y="Risk",color="Grade",title="Watchlist Forensic Risk"),use_container_width=True)
            st.plotly_chart(px.bar(watch_df,x="Ticker",y="ROIC",color="Grade",title="Watchlist ROIC"),use_container_width=True)
        if errors:
            with st.expander("Errors"): st.dataframe(pd.DataFrame(errors),use_container_width=True)

with tab_compare:
    st.subheader("Compare")
    compare_input=st.text_input("Tickers separated by comma","NVDA, AVGO, AMD",key="compare_tickers")
    if st.button("Run Compare",key="compare_button"):
        tickers=[x.strip().upper() for x in compare_input.split(",") if x.strip()]
        rows=[]; errors=[]
        for t in tickers:
            try:
                with st.spinner(f"Analyzing {t}..."): rows.append(latest_row_for_table(run_forensic_engine(t,wacc=wacc)))
            except Exception as e: errors.append({"Ticker":t,"Error":str(e)})
        if rows:
            compare_df=pd.DataFrame(rows); st.dataframe(compare_df,use_container_width=True)
            metrics=["ROIC","Accrual","CFO/NI","SBC/Revenue","Risk"]
            melted=compare_df.melt(id_vars=["Ticker"],value_vars=[m for m in metrics if m in compare_df.columns],var_name="Metric",value_name="Value")
            st.plotly_chart(px.bar(melted,x="Metric",y="Value",color="Ticker",barmode="group",title="Cross-Ticker Comparison"),use_container_width=True)
        if errors:
            with st.expander("Errors"): st.dataframe(pd.DataFrame(errors),use_container_width=True)

with tab_screening:
    st.subheader("Screening")
    st.caption("Small default universe for speed. Add more tickers manually if needed.")
    universe_text=st.text_area("Universe tickers",", ".join(DEFAULT_UNIVERSE),height=100)
    c1,c2,c3=st.columns(3)
    with c1: roic_min_pct=st.slider("ROIC minimum (%)",-200.0,200.0,20.0,5.0)
    with c2: risk_max=st.slider("Risk maximum",0,100,40,5)
    with c3: accrual_max_pct=st.slider("Accrual maximum (%)",-100.0,100.0,5.0,5.0)
    if st.button("Run Screen",key="screen_button"):
        universe=[x.strip().upper() for x in universe_text.replace("\n",",").split(",") if x.strip()]
        rows=[]; errors=[]; progress=st.progress(0)
        for i,t in enumerate(universe):
            try:
                with st.spinner(f"Screening {t}..."): rows.append(latest_row_for_table(run_forensic_engine(t,wacc=wacc)))
            except Exception as e: errors.append({"Ticker":t,"Error":str(e)})
            progress.progress((i+1)/max(len(universe),1))
        if rows:
            raw_df=pd.DataFrame(rows)
            screen_df=raw_df[(raw_df["ROIC"].fillna(-999)>=roic_min_pct/100)&(raw_df["Risk"].fillna(999)<=risk_max)&(raw_df["Accrual"].fillna(999)<=accrual_max_pct/100)].copy()
            st.markdown("### Screen Results"); st.dataframe(screen_df,use_container_width=True)
            with st.expander("All Screened Tickers"): st.dataframe(raw_df,use_container_width=True)
            if not screen_df.empty:
                st.plotly_chart(px.scatter(screen_df,x="Risk",y="ROIC",size="Quality",color="Grade",hover_name="Ticker",title="Screened Candidates: ROIC vs Risk"),use_container_width=True)
        if errors:
            with st.expander("Errors"): st.dataframe(pd.DataFrame(errors),use_container_width=True)

st.caption("v2.0: card-centered UX + Watchlist + Compare + Screening. TTM uses pragmatic approximation; full quarterization remains future work.")
