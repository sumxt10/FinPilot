from __future__ import annotations

"""Goal, life-event, financial-twin, and readiness planning tools."""

from .shared_agent import NEEDS

def goal_plan(target,months,saved,surplus): need=(target-saved)/months; return dict(monthly_needed=need,feasible=surplus>=need,gap=max(need-surplus,0))
def simulate_purchase(price,down,rate,years,state):
    P=price*(1-down); r=rate/1200; n=years*12; emi=P*r*(1+r)**n/((1+r)**n-1); inc=state["income"]; surplus=inc-state["health"]["avg_spend"]-emi
    return dict(emi=emi,new_surplus=surplus,new_savings_rate=surplus/inc,down_payment=price*down,verdict="Affordable" if surplus>=.1*inc else "Risky" if surplus>=0 else "Unaffordable")
def twin(state,scenario,**k):
    h=state["health"]; ess=sum(state["spending"]["monthly"][c].iloc[-3:].mean() for c in NEEDS if c in state["spending"]["monthly"])
    if scenario=="Job loss": return dict(runway_months=state["balance"]/max(ess+0.3*h["avg_spend"],1))
    if scenario=="Salary increase": inc=state["income"]*(1+k["pct"]/100); return dict(new_savings_rate=(inc-h["avg_spend"])/inc,extra_monthly=inc-state["income"])
    if scenario=="New loan": return dict(new_savings_rate=(state["income"]-h["avg_spend"]-k["emi"])/state["income"])
def readiness(state):
    e=state["health"]["emergency_months"]; ok=e>=6 and state["health"]["debt_ratio"]<.3
    return dict(ready=ok,text="Ready to increase investment risk." if ok else f"Not yet: complete emergency fund first ({e:.1f}/6 months) before increasing risk.")
