from __future__ import annotations

"""Anomaly Detection Agent."""

from .spending_agent import _spend

def detect_anomalies(df):
    out=[]; d=_spend(df)
    for i,r in d.iterrows():
        h=d[(d.merchant==r.merchant)&(d.index!=i)].amount
        if len(h)<3: h=d[(d.category==r.category)&(d.index!=i)].amount
        med=h.median() if len(h) else 0; mad=(h-med).abs().median()*1.4826 if len(h) else 0
        z=(r.amount-med)/(mad+1)
        if r.amount>5000 and (z>6 or len(h)<3) and r.amount>3*max(med,1):
            out.append(dict(kind="Potential Fraud / Unusual",merchant=r.merchant,date=r.date.date(),amount=r.amount,reason=f"₹{r.amount:,.0f} is far above the usual ₹{med:,.0f} for {r.category}.",severity="critical"))
    g=d[d.category.isin(["Subscriptions","Bills","Debt/EMI"])].sort_values("date")
    for (m,a),x in g.groupby(["merchant","amount"]):
        ds=x.date.sort_values().tolist()
        for p,q in zip(ds,ds[1:]):
            if (q-p).days<=5: out.append(dict(kind="Duplicate Charge",merchant=m,date=q.date(),amount=a,reason=f"{m} charged ₹{a:,.0f} twice within {(q-p).days} days.",severity="high"))
    return out
