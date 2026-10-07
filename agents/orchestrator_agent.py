from __future__ import annotations

"""Master Orchestrator Agent."""
import time

from .ingestion_agent import ingest
from .categorization_agent import categorize
from .spending_agent import analyze_spending
from .budget_agent import plan_budget
from .health_agent import health_score
from .anomaly_agent import detect_anomalies
from .subscriptions_agent import analyze_subscriptions
from .forecast_agent import forecast
from .advisor_agent import advise, llm_narrate
from .notifications_agent import notify

# ---- Agent 11: Master Orchestrator (Planner → Executor → Reviewer) -----------
def review(state):
    bad=[a for a in state["advice"] if not a["why"] or a["saving"]<0]; return dict(approved=not bad,rejected=len(bad))
def run_pipeline(raw,profile,overrides=None):
    S=dict(trace=[])
    def t(n,f,sm):
        t0=time.time(); r=f(); S["trace"].append(dict(agent=n,status="OK",ms=round((time.time()-t0)*1000,1),summary=sm(r))); return r
    plan=["ingest","categorize","analyze","budget","health","anomaly","subscriptions","forecast","advise","notify","review"]
    S["trace"].append(dict(agent="Master Orchestrator (Planner)",status="OK",ms=0,summary="Plan: "+" → ".join(plan)))
    d=t("1 Data Ingestion",lambda:ingest(raw),lambda x:f"{len(x)} transactions normalised")
    S["df"]=df=t("2 Categorization",lambda:categorize(d,overrides),lambda x:f"{x.category.nunique()} categories, {(x.confidence<.5).sum()} low-confidence")
    S["income"]=income=profile.get("monthly_income") or df[df.type=="credit"].groupby("month").amount.sum().mean()
    S["balance"]=balance=profile.get("opening_balance",0)+df[df.type=="credit"].amount.sum()-df[df.type=="debit"].amount.sum()
    S["spending"]=t("3 Spending Analysis",lambda:analyze_spending(df),lambda x:f"{len(x['insights'])} insights")
    S["budget"]=t("4 Budget Management",lambda:plan_budget(df,income,profile.get("budget_split")),lambda x:f"needs {x['buckets']['needs']['util']:.0%}, wants {x['buckets']['wants']['util']:.0%} used")
    S["health"]=t("5 Financial Health",lambda:health_score(df,income,balance),lambda x:f"score {x['score']}/100")
    S["anomalies"]=t("6 Anomaly Detection",lambda:detect_anomalies(df),lambda x:f"{len(x)} anomalies")
    S["subs"]=t("7 Subscription Intelligence",lambda:analyze_subscriptions(df,profile.get("subscription_last_used",{}),df.date.max()),lambda x:f"{len(x)} subscriptions, {sum(s['unused'] for s in x)} unused")
    S["forecast"]=t("8 Cash-Flow Forecast",lambda:forecast(df,balance,25,profile.get("min_buffer",5000)),lambda x:f"risk {x['risk']}, min ₹{x['min_balance']:,.0f}")
    S["advice"]=t("9 Financial Advisor",lambda:advise(S),lambda x:f"{len(x)} recommendations")
    S["alerts"]=t("10 Alert & Notification",lambda:notify(S),lambda x:f"{len(x)} alerts queued")
    S["review"]=t("Reviewer (guardrail)",lambda:review(S),lambda x:"approved" if x["approved"] else f"{x['rejected']} rejected")
    S["narrative"]=llm_narrate(S); return S
