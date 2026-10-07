from __future__ import annotations

"""Financial Health Scoring Agent."""
import numpy as np
import pandas as pd

from .spending_agent import _spend

def health_score(df,income,balance):
    sp=_spend(df); m=sp.groupby("month").amount.sum()
    if m.empty:
        parts=dict(savings_rate=0.0,debt_ratio=0.0,consistency=0.0,emergency_fund=0.0)
        return dict(score=0,parts=parts,savings_rate=0.0,debt_ratio=0.0,emergency_months=0.0,avg_spend=0.0,has_spending_data=False)
    avg_spend=float(m.mean()); income=float(income) if pd.notna(income) else 0.0
    emi=df[df.category=="Debt/EMI"].groupby("month").amount.sum().mean(); emi=0 if np.isnan(emi) else emi
    sr=max(income-avg_spend,0)/income if income>0 else 0.0
    dr=emi/income if income>0 else 0.0; cons=1-min((m.std()/avg_spend) if len(m)>1 and avg_spend else 0,1); ef=balance/max(avg_spend,1)
    parts=dict(savings_rate=min(sr/.2,1)*30,debt_ratio=max(1-dr/.4,0)*20,consistency=cons*20,emergency_fund=min(ef/6,1)*30)
    return dict(score=round(sum(parts.values())),parts={k:round(v,1) for k,v in parts.items()},savings_rate=sr,debt_ratio=dr,emergency_months=ef,avg_spend=avg_spend,has_spending_data=True)
