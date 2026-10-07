from __future__ import annotations

"""Cash-Flow Forecasting Agent."""
import pandas as pd

def forecast(df,balance,horizon=25,buffer=5000):
    today=df.date.max(); d=df[df.type=="debit"]; rec=[]
    for m,x in d.groupby("merchant"):
        if x.month.nunique()>=4 and x.amount.std()<0.15*x.amount.mean() or (x.category.iloc[0] in("Bills","Debt/EMI","Investments") and x.month.nunique()>=4 and x.amount.std()<0.3*x.amount.mean()):
            rec.append((int(x.date.dt.day.median()),x.groupby("month").amount.sum().mean()))
    rec_merch=set(m for m,x in d.groupby("merchant") if x.month.nunique()>=4 and x.amount.std()<0.3*x.amount.mean())
    var=d[~d.merchant.isin(rec_merch)&(d.category!="Investments")]; last=today-pd.Timedelta(days=90)
    daily=var[var.date>last].amount.sum()/90
    sal=df[df.type=="credit"]; sd=int(sal.date.dt.day.median()); inc=sal.groupby("month").amount.sum().mean()
    rows=[];b=balance
    for i in range(1,horizon+1):
        day=today+pd.Timedelta(days=i); b-=daily
        for dd,a in rec:
            if day.day==dd: b-=a
        if day.day==sd: b+=inc
        rows.append(dict(date=day,balance=b))
    f=pd.DataFrame(rows); mn=f.balance.min()
    return dict(series=f,daily_variable=daily,min_balance=mn,end_balance=f.balance.iloc[-1],risk="HIGH" if mn<0 else "MEDIUM" if mn<buffer else "LOW",current=balance)
