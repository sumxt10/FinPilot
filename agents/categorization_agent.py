from __future__ import annotations

"""Transaction Categorization Agent."""
import re
import pandas as pd

from .shared_agent import CATS

def categorize(df,overrides=None):
    overrides=overrides or {}; cats=[];conf=[]
    for m,t in zip(df.merchant,df.type):
        ml=re.sub(r"[^a-z0-9]+", " ", m.lower()).strip()
        if m in overrides: cats.append(overrides[m]);conf.append(1.0);continue
        def matches(keyword):
            normalized = re.sub(r"[^a-z0-9]+", " ", keyword.lower()).strip()
            return bool(re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", ml))
        hit=next((c for c,k in CATS.items() if any(matches(w) for w in k)),None)
        if t=="credit": hit=hit if hit=="Income" else "Income"
        cats.append(hit or "Others"); conf.append(0.95 if hit else 0.4)
    o=df.copy(); o["category"]=cats; o["confidence"]=conf; o["month"]=o.date.dt.to_period("M").astype(str); return o
