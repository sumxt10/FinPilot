from __future__ import annotations

"""Alert and Notification Agent."""
from .shared_agent import SEV

def notify(state):
    a=[]
    for x in state["anomalies"]: a.append(dict(severity=x["severity"],type=x["kind"],text=f"{x['kind']}: {x['reason']}",channel="SMS + App"))
    for c,v in state["budget"]["categories"].items():
        if v["util"]>=.9: a.append(dict(severity="high" if v["util"]>1 else "medium",type="Budget Risk",text=f"{c} budget {v['util']:.0%} utilised.",channel="App"))
    for s in state["subs"]:
        if s["unused"]: a.append(dict(severity="medium",type="Subscription",text=f"Unused subscription {s['merchant']} (₹{s['annual']:,.0f}/yr).",channel="Email"))
    if state["health"]["savings_rate"]<.2: a.append(dict(severity="medium",type="Savings",text=f"Savings rate {state['health']['savings_rate']:.0%} is below the 20% target.",channel="App"))
    f=state["forecast"]
    if f["risk"]!="LOW": a.append(dict(severity="critical" if f["risk"]=="HIGH" else "high",type="Cash Flow",text=f"Projected minimum balance ₹{f['min_balance']:,.0f} in next 25 days.",channel="SMS + App"))
    return sorted(a,key=lambda x:SEV[x["severity"]])
