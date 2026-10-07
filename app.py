import json, os, pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
import agents as A
from data.generate_data import make
st.set_page_config(page_title="FinPilot - AI Financial Wellness Agent",page_icon=":material/account_balance:",layout="wide")
st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
.finpilot-subtitle {color: var(--text-color); opacity: .78; margin-top: 0; margin-bottom: 1.25rem;}
[data-testid="stMetric"] {background: var(--secondary-background-color); border: 1px solid rgba(128, 128, 128, .28); border-radius: 12px; padding: .75rem;}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {color: var(--text-color) !important;}
[data-testid="stAlert"], [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] {color: var(--text-color);}
[data-testid="stDataFrame"] {border: 1px solid rgba(128, 128, 128, .28); border-radius: 10px;}
.finpilot-card-title {color: var(--text-color); font-size: 1.15rem; font-weight: 650; margin-bottom: .75rem;}
</style>
""",unsafe_allow_html=True)
if not os.path.exists("data/transactions.csv"): make()
inr=lambda v:f"₹{v:,.0f}"
with st.sidebar:
    st.title("FinPilot"); st.caption("Autonomous financial wellness agent")
    st.success("11-agent workflow · MCP ready", icon=":material/check_circle:")
    src=st.radio("Data source",["Sample statement (12 months)","Upload CSV / JSON / PDF"])
    prof=json.load(open("data/profile.json")); up=None
    if src.startswith("Upload"):
        up=st.file_uploader("Bank / UPI / card statement",type=["csv","json","pdf"])
        st.caption("Columns: date, description, amount, type (or debit/credit columns). PDF uploads are parsed as text statements.")
        prof["opening_balance"]=st.number_input("Opening balance (₹)",0,10**8,100000)
        prof["monthly_income"]=st.number_input("Monthly income (₹)",0,10**8,50000); prof["subscription_last_used"]={}
    if "ov" not in st.session_state: st.session_state.ov={}
    st.caption("🧠 Optional: set GROQ_API_KEY in .env or .streamlit/secrets.toml for LLM narrative")
    st.caption("Example: GROQ_API_KEY=your_key_here")
if up is not None:
    if up.name.lower().endswith(".pdf"):
        raw = A.parse_pdf_file(up.getvalue())
    elif up.name.lower().endswith(".json"):
        raw = json.load(up)
    else:
        raw = pd.read_csv(up)
elif src.startswith("Upload"): st.info("Upload a statement in the sidebar."); st.stop()
else: raw=pd.read_csv("data/transactions.csv")
raw = A.ingest(raw)
S=A.run_pipeline(raw,prof,st.session_state.ov); df=S["df"]; h=S["health"]; f=S["forecast"]
if not h.get("has_spending_data", True):
    st.warning("No expense transactions were detected. Check that the statement includes debit/expense rows with transaction dates and amounts.")
rag_context=A.build_rag_context(S); llm_summary=A.llm_narrate(S)

st.header("AI CFO · Personal Finance Agent")
st.title("Your financial overview")
st.markdown(f'<div class="finpilot-subtitle">{len(df)} transactions normalized · {df.date.min().date()} to {df.date.max().date()} · deterministic analysis grounded by RAG</div>',unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="finpilot-card-title">AI coach summary</div>',unsafe_allow_html=True)
    col1, col2 = st.columns([2,1])
    with col1:
        if isinstance(llm_summary, dict):
            st.write(llm_summary.get("summary", "No summary available."))
            st.write(f"**Risk level:** {llm_summary.get('risk_level', f['risk'])}")
            st.write(f"**Confidence:** {llm_summary.get('confidence', 0.8):.0%}")
            if llm_summary.get("key_actions"):
                st.write("**Recommended actions:**")
                for action in llm_summary["key_actions"][:3]:
                    st.markdown(f"- {action}")
        else:
            st.info(llm_summary)
    with col2:
        with st.container(horizontal=True):
            st.metric("Health score", f"{h['score']}/100", border=True)
            st.metric("Savings rate", f"{h['savings_rate']:.0%}", border=True)
            st.metric("Emergency cushion", f"{h['emergency_months']:.1f} mo", border=True)

    with st.expander("Financial guidance behind this summary", icon=":material/menu_book:"):
        for fact in rag_context["facts"][:5]:
            st.write(f"- {fact.get('title', 'Rule')}: {fact.get('content', '')}")


tabs=st.tabs([":material/home: Overview",":material/bar_chart: Spending",":material/warning: Anomalies",":material/ssid_chart: Forecast",":material/lightbulb: Advice",":material/target: Planner",":material/account_tree: Agent trace",":material/receipt_long: Transactions"])
with tabs[0]:
    with st.container(horizontal=True):
        st.metric("Health score",f"{h['score']}/100",border=True)
        st.metric("Balance",inr(S['balance']),border=True)
        st.metric("Savings rate",f"{h['savings_rate']:.0%}",border=True)
        st.metric("Emergency fund",f"{h['emergency_months']:.1f} mo",border=True)
        st.metric("Cash-flow risk",f['risk'],f"{len(S['alerts'])} active alerts",border=True)
    a,b=st.columns([1,2])
    g=go.Figure(go.Indicator(mode="gauge+number",value=h["score"],gauge=dict(axis=dict(range=[0,100]),bar=dict(color="#2b8be0"))));g.update_layout(height=260,margin=dict(t=20,b=0)); a.plotly_chart(g,width="stretch")
    pf=pd.DataFrame(dict(factor=list(h["parts"]),points=list(h["parts"].values()))); b.plotly_chart(px.bar(pf,x="factor",y="points",title="Score breakdown (max 30/20/20/30)",color_discrete_sequence=["#2b8be0"]),width="stretch")
    st.subheader("Top alerts")
    if not S["alerts"]:
        st.success("No active alerts. Keep monitoring your financial baseline.")
    for x in S["alerts"][:5]:
        with st.container(border=True):
            st.markdown(f"**{x['type']}** · {x['text']}")
with tabs[1]:
    m=S["spending"]["monthly"]; st.plotly_chart(px.bar(m.reset_index().melt("month"),x="month",y="value",color="category",title="Monthly spend by category"),width="stretch")
    bu=S["budget"]; c1,c2=st.columns(2)
    for c,n in zip((c1,c2),("needs","wants")): c.metric(f"{n.title()} ({bu['month']})",f"{inr(bu['buckets'][n]['spent'])} / {inr(bu['buckets'][n]['target'])}",f"{bu['buckets'][n]['util']:.0%} used",delta_color="inverse")
    cb=pd.DataFrame(bu["categories"]).T.reset_index().rename(columns={"index":"category"}); st.dataframe(cb.style.format({"cap":"₹{:,.0f}","spent":"₹{:,.0f}","util":"{:.0%}"}),hide_index=True,width="stretch")
    for i in S["spending"]["insights"]: st.warning(i["text"])
with tabs[2]:
    st.subheader("Anomaly Detection"); 
    for x in S["anomalies"]: st.error(f"**{x['kind']}** — {x['merchant']} on {x['date']}: {x['reason']}")
    if not S["anomalies"]: st.success("No anomalies")
    st.subheader("Subscription Intelligence"); sd=pd.DataFrame(S["subs"]); st.dataframe(sd,hide_index=True,width="stretch")
    st.metric("Potential yearly saving from cancelling unused",inr(sum(s["annual"] for s in S["subs"] if s["unused"])))
with tabs[3]:
    fs=f["series"]; fig=px.area(fs,x="date",y="balance",title="Projected balance – next 25 days"); fig.add_hline(y=prof.get("min_buffer",5000),line_dash="dash",line_color="red"); st.plotly_chart(fig,width="stretch")
    c=st.columns(3); c[0].metric("Current",inr(f["current"])); c[1].metric("Lowest projected",inr(f["min_balance"])); c[2].metric("In 25 days",inr(f["end_balance"]))
    st.caption(f"Variable spend ≈ {inr(f['daily_variable'])}/day; recurring bills & salary simulated by date.")
with tabs[4]:
    st.subheader("Recommendations (Reviewer: "+("✅ approved" if S["review"]["approved"] else "❌ rejected")+")")
    for r in S["advice"]: st.markdown(f"**{r['title']}** — est. saving {inr(r['saving'])}/yr  \n<small>{r['why']}</small>",unsafe_allow_html=True)
    st.metric("Total potential annual savings",inr(sum(r["saving"] for r in S["advice"])))
    st.subheader("Notification queue")
    st.dataframe(pd.DataFrame(S["alerts"]),hide_index=True,width="stretch")
with tabs[5]:
    st.subheader("Goal-based planning"); a,b,c=st.columns(3); t=a.number_input("Target (₹)",value=500000); mo=b.number_input("Months",value=24); sv=c.number_input("Already saved",value=0)
    surplus=S["income"]-h["avg_spend"]; gp=A.goal_plan(t,mo,sv,surplus); st.write(f"Need **{inr(gp['monthly_needed'])}/month**; current surplus {inr(surplus)} → "+("✅ feasible" if gp["feasible"] else f"⚠️ short by {inr(gp['gap'])}/month"))
    st.subheader("Life-event simulation: buy a car"); a,b,c,d=st.columns(4); p=a.number_input("Price",value=1200000); dp=b.slider("Down %",0,50,20)/100; r=c.number_input("Rate %",value=9.0); y=d.slider("Years",1,8,5)
    sim=A.simulate_purchase(p,dp,r,y,S); st.write(f"EMI **{inr(sim['emi'])}** · surplus after EMI {inr(sim['new_surplus'])} · savings rate {sim['new_savings_rate']:.0%} → **{sim['verdict']}**")
    st.subheader("Financial Twin"); sc=st.selectbox("Scenario",["Job loss","Salary increase","New loan"])
    if sc=="Job loss": st.write(f"Runway: **{A.twin(S,sc)['runway_months']:.1f} months**")
    elif sc=="Salary increase": o=A.twin(S,sc,pct=st.slider("Raise %",5,50,15)); st.write(f"New savings rate {o['new_savings_rate']:.0%} (+{inr(o['extra_monthly'])}/mo)")
    else: st.write(f"New savings rate {A.twin(S,sc,emi=st.number_input('New EMI',value=8000))['new_savings_rate']:.0%}")
    st.subheader("Investment readiness"); rd=A.readiness(S); (st.success if rd["ready"] else st.warning)(rd["text"])
with tabs[6]:
    st.subheader("Agent execution trace (Planner → Executor → Reviewer)")
    st.caption("Every number in the dashboard is produced by a deterministic agent and recorded here for review.")
    st.dataframe(pd.DataFrame(S["trace"]),hide_index=True,width="stretch")
    st.info("MCP tools: `finpilot_normalize_transactions` and `finpilot_analyze_transactions` are available over JSON-RPC stdio via `python mcp_server.py`.")
with tabs[7]:
    st.caption("Fix a category – the Categorization agent learns the override.")
    low=df[df.confidence<.5].merchant.unique().tolist() or df.merchant.unique().tolist()
    a,b=st.columns(2); mm=a.selectbox("Merchant",low); cc=b.selectbox("Category",list(A.CATS)+["Others"])
    if st.button("Teach agent"): st.session_state.ov[mm]=cc; st.rerun()
    st.dataframe(df.drop(columns=[c for c in ["true_category"] if c in df]),hide_index=True,width="stretch")
