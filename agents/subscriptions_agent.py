from __future__ import annotations

"""Subscription Intelligence Agent."""
import pandas as pd

def analyze_subscriptions(df,last_used,today):
    s=df[(df.category=="Subscriptions")&(df.type=="debit")]; out=[]
    for m,x in s.groupby("merchant"):
        amt=x.amount.mode().iloc[0]; lu=pd.to_datetime(last_used.get(m,today)); idle=(today-lu).days/30
        out.append(dict(merchant=m,monthly=amt,months_seen=x.month.nunique(),idle_months=round(idle,1),annual=amt*12,unused=idle>=3,action="Cancel" if idle>=3 else "Keep"))
    return out
