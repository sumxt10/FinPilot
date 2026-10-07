from __future__ import annotations

"""Spending Pattern Analysis Agent."""
import pandas as pd

def _spend(df): return df[(df.type=="debit")&(df.category!="Investments")]

def analyze_spending(df):
    sp=_spend(df); pv=sp.pivot_table(index="month",columns="category",values="amount",aggfunc="sum",fill_value=0)
    ins=[]
    if len(pv)>=3:
        for c in pv.columns:
            v=pv[c].values[-3:]
            if v[0]>0 and v[0]<v[1]<v[2] and (v[2]-v[0])/v[0]>0.15:
                ins.append(dict(type="trend",category=c,severity="medium",text=f"{c} spending rising {((v[2]/v[0])**.5-1)*100:.0f}% per month (₹{v[0]:,.0f} → ₹{v[2]:,.0f}).",monthly_growth=(v[2]/v[0])**.5-1))
        cur=pv.iloc[-1]; base=pv.iloc[:-1].mean()
        for c in pv.columns:
            if base[c]>0 and cur[c]>2*base[c] and cur[c]-base[c]>1000:
                ins.append(dict(type="spike",category=c,severity="high",text=f"{c} is ₹{cur[c]:,.0f} this month vs usual ₹{base[c]:,.0f} ({cur[c]/base[c]:.1f}x)."))
    return dict(monthly=pv,insights=ins)
