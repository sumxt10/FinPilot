from __future__ import annotations

"""Budget Management Agent."""
import pandas as pd

from .shared_agent import NEEDS, WANTS
from .spending_agent import _spend

def plan_budget(df,income,custom=None):
    sp=_spend(df); pv=sp.pivot_table(index="month",columns="category",values="amount",aggfunc="sum",fill_value=0)
    cur=pv.iloc[-1] if not pv.empty else pd.Series(dtype=float)
    prev=pv.iloc[:-1].mean() if len(pv)>1 else cur
    split=custom or dict(needs=.5,wants=.3,savings=.2)
    b=dict(needs=dict(target=income*split["needs"],spent=sum(cur.get(c,0) for c in NEEDS)),
           wants=dict(target=income*split["wants"],spent=sum(cur.get(c,0) for c in WANTS)))
    for k in b: b[k]["util"]=b[k]["spent"]/b[k]["target"] if b[k]["target"] else 0
    caps={c:dict(cap=prev[c]*1.1,spent=cur[c],util=cur[c]/(prev[c]*1.1)) for c in pv.columns if prev[c]>0}
    month=pv.index[-1] if not pv.empty else (df["month"].max() if not df.empty else "N/A")
    return dict(buckets=b,categories=caps,month=month)
