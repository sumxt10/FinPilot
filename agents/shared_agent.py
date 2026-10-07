"""FinPilot: 11 role-based agents + Planner/Reviewer orchestration (deterministic core, optional Groq narration)."""
import os, time, json, datetime as dt, re
import numpy as np, pandas as pd

CATS={"Income":["salary","interest","refund"],"Debt/EMI":["emi","loan"],"Investments":["sip","mutual fund","zerodha","groww"],
"Subscriptions":["netflix","spotify","prime","chatgpt","gym","hotstar"],"Bills":["electricity","rent","broadband","jio","airtel","water","gas"],
"Food & Dining":["swiggy","zomato","bigbasket","dominos","restaurant","cafe","blinkit"],"Transportation":["uber","ola","fuel","petrol","pump","metro","irctc"],
"Shopping":["amazon","flipkart","myntra","ajio"],"Healthcare":["pharmacy","apollo","hospital","clinic"],"Education":["udemy","coursera","tuition","school"]}
NEEDS=["Bills","Healthcare","Debt/EMI","Transportation","Education"]; WANTS=["Food & Dining","Shopping","Subscriptions","Others"]
SEV={"critical":0,"high":1,"medium":2,"info":3}


def _load_env_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"), override=False)
    except Exception:
        pass


def get_groq_api_key():
    _load_env_file()
    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key.strip():
        return api_key.strip()
    try:
        import streamlit as st
        secret = st.secrets.get("GROQ_API_KEY")
        if secret:
            return str(secret).strip()
    except Exception:
        pass
    return None


def _fallback_kb():
    return [
        {"title": "Emergency fund", "content": "A strong emergency fund covers 6 months of essential expenses and protects against income shocks."},
        {"title": "Savings rate", "content": "A healthy savings rate is at least 20% of monthly income, with a goal of increasing savings gradually each year."},
        {"title": "Debt management", "content": "Keep debt payments controlled so total recurring liabilities stay below 30% to 35% of monthly income."},
        {"title": "Subscription cleanup", "content": "Unused subscriptions should be cancelled if not consumed for 90 days or more to preserve cash flow."},
        {"title": "Cash-flow risk", "content": "Maintain a minimum balance buffer and watch for spikes in essentials, travel, utilities, and recurring charges."},
        {"title": "Budgeting", "content": "Needs should be kept within roughly 50% of income, wants within 30%, and savings or debt reduction within 20%."},
        {"title": "Anomaly detection", "content": "Large one-off payments, duplicated charges, or recurring merchants with sudden spikes should be investigated as possible fraud or billing errors."},
    ]


def load_rag_kb(path=None):
    if path is None:
        path = os.path.join(os.getcwd(), "docs", "financial_kb.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return _fallback_kb()


def _tokenize(text):
    text = re.sub(r"[^a-z0-9\s]", " ", str(text).lower())
    return [w for w in text.split() if len(w) > 2]


def retrieve_rag_facts(query, kb=None, top_k=4):
    kb = kb or load_rag_kb()
    query_tokens = set(_tokenize(query))
    scored = []
    for item in kb:
        text = f"{item.get('title','')} {item.get('content','')}"
        tokens = set(_tokenize(text))
        overlap = len(query_tokens.intersection(tokens))
        score = overlap + 0.2 * sum(1 for t in query_tokens if t in text.lower())
        scored.append((score, item))
    ranked = sorted(scored, reverse=True, key=lambda x: x[0])
    facts = [item for _, item in ranked[:top_k] if item]
    if not facts:
        return kb[:top_k]
    return facts


def build_rag_context(state):
    income = state.get("income", 0)
    health = state.get("health", {})
    savings_rate = health.get("savings_rate", 0)
    emergency_months = health.get("emergency_months", 0)
    forecast = state.get("forecast", {})
    alerts = state.get("alerts", [])
    spending = state.get("spending", {})
    monthly = spending.get("monthly", pd.DataFrame())
    top_category = "None"
    if hasattr(monthly, "columns") and not monthly.empty:
        current_row = monthly.iloc[-1] if len(monthly) else pd.Series()
        if not current_row.empty:
            top_category = current_row.idxmax() if not current_row.empty else "None"

    query = (
        f"User income is ₹{income:,.0f}, savings rate {savings_rate:.2%}, emergency fund {emergency_months:.1f} months, "
        f"top spend category is {top_category}, minimum forecast balance is ₹{forecast.get('min_balance', 0):,.0f}, "
        f"and current alerts are {', '.join(a.get('type', 'general') for a in alerts[:3])}."
    )
    kb = load_rag_kb()
    facts = retrieve_rag_facts(query, kb, top_k=5)
    return {"query": query, "facts": facts}


def groq_chat(prompt, system_msg=None, model=None, api_key=None):
    api_key = api_key or get_groq_api_key()
    if not api_key:
        return None
    model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg or "You are a careful personal finance advisor. Use the provided financial context and do not invent numbers."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }
    try:
        import requests
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _parse_amount(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if not text:
        return np.nan
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    text = text.replace("₹", "").replace("$", "").replace(",", "").replace(" ", "")
    text = text.replace("CR", "").replace("DR", "")
    if text.lower().startswith("dr"):
        negative = True
        text = text[2:]
    if text.lower().startswith("cr"):
        text = text[2:]
    if text.startswith("-"):
        negative = True
        text = text[1:]
    if text.startswith("+"):
        text = text[1:]
    try:
        number = float(text)
    except ValueError:
        try:
            number = float(text.replace("-", ""))
        except ValueError:
            return np.nan
    return -abs(number) if negative else abs(number)


def parse_pdf_text(raw_text):
    rows = []
    for line in str(raw_text).splitlines():
        line = line.strip()
        if not line or line.lower().startswith("statement"):
            continue
        match = re.search(r"(\d{1,2}[/-][A-Za-z]{3,9}[/-]\d{2,4})\s*,\s*([^,]+?)\s*,\s*(.+)", line)
        if not match:
            continue
        date_str, merchant, amount_text = match.groups()
        amount = _parse_amount(amount_text)
        if pd.isna(amount):
            continue
        rows.append({
            "date": date_str,
            "merchant": merchant.strip().title(),
            "amount": float(amount),
            "type": "debit" if amount < 0 else "credit",
        })
    return rows


def parse_pdf_file(file_path_or_bytes):
    try:
        import pdfplumber
    except ImportError as exc:
        raise ImportError("pdfplumber is required to parse PDF statements. Install it with pip install pdfplumber.") from exc

    if isinstance(file_path_or_bytes, (bytes, bytearray)):
        import io
        text = ""
        with pdfplumber.open(io.BytesIO(file_path_or_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or "\n"
        return pd.DataFrame(parse_pdf_text(text))

    with pdfplumber.open(file_path_or_bytes) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    return pd.DataFrame(parse_pdf_text(text))


# ---- Agent 1: Data Ingestion -------------------------------------------------
def ingest(src):
    if isinstance(src, (bytes, bytearray)):
        return parse_pdf_file(src)
    if isinstance(src, str) and src.lower().endswith(".pdf"):
        return parse_pdf_file(src)
    if isinstance(src, pd.DataFrame):
        df = src.copy()
    elif isinstance(src, list):
        df = pd.DataFrame.from_records(src)
    elif isinstance(src, dict):
        account = src.get("Account")
        if isinstance(account, dict) and isinstance(account.get("Transactions"), dict):
            payload = account["Transactions"].get("Transaction", [])
        else:
            payload = next(
                (src[key] for key in ("transactions", "data", "records", "results", "items") if key in src),
                src,
            )
        if isinstance(payload, list):
            df = pd.DataFrame.from_records(payload)
        elif isinstance(payload, dict):
            if payload and all(isinstance(value, dict) for value in payload.values()):
                df = pd.DataFrame.from_dict(payload, orient="index")
            else:
                df = pd.DataFrame(payload)
        else:
            raise ValueError("JSON statement must contain transaction records.")
    elif isinstance(src, str) and src.lower().endswith(".json"):
        with open(src, "r", encoding="utf-8") as f:
            return ingest(json.load(f))
    else:
        df = pd.read_csv(src)

    df.columns = [str(c).strip().lower() for c in df.columns]
    alias = {"narration": "description", "merchant": "description", "details": "description", "txn date": "date", "txn_date": "date", "value date": "date", "valuedate": "date", "posted date": "date", "transaction date": "date", "transaction_date": "date", "transactiondate": "date", "transaction timestamp": "date", "transactiontimestamp": "date", "transaction_type": "type", "transaction type": "type", "transactiontype": "type", "txn_type": "type", "txn type": "type", "direction": "type", "debit": "debit_amt", "credit": "credit_amt", "debit_amt": "debit_amt", "credit_amt": "credit_amt"}
    df = df.rename(columns={k: v for k, v in alias.items() if k in df.columns})
    if not df.columns.is_unique:
        df = pd.concat(
            [df.loc[:, df.columns == column].bfill(axis=1).iloc[:, 0].rename(column) for column in dict.fromkeys(df.columns)],
            axis=1,
        )

    if "amount" in df.columns:
        df["amount"] = df["amount"].apply(_parse_amount)
    if "debit_amt" in df.columns or "credit_amt" in df.columns:
        debit = pd.to_numeric(df.get("debit_amt"), errors="coerce").fillna(0)
        credit = pd.to_numeric(df.get("credit_amt"), errors="coerce").fillna(0)
        df["amount"] = debit + credit
        df["type"] = np.where(credit > 0, "credit", "debit")
    if "debit_amt" in df.columns:
        df["debit_amt"] = df["debit_amt"].apply(_parse_amount)
    if "credit_amt" in df.columns:
        df["credit_amt"] = df["credit_amt"].apply(_parse_amount)

    if "date" not in df.columns:
        df["date"] = pd.to_datetime(df.index, errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if isinstance(df["date"].dtype, pd.DatetimeTZDtype):
        df["date"] = df["date"].dt.tz_localize(None)
    df["amount"] = pd.to_numeric(df.get("amount"), errors="coerce")
    if "type" not in df.columns:
        if "debit_amt" in df.columns and "credit_amt" in df.columns:
            df["type"] = np.where(df["credit_amt"] > 0, "credit", "debit")
        else:
            df["type"] = np.where(df["amount"] < 0, "debit", "credit")
    df["type"] = df["type"].fillna("debit").astype(str).str.lower().str.strip()
    df["type"] = df["type"].replace({"expense": "debit", "expenses": "debit", "withdrawal": "debit", "withdraw": "debit", "payment": "debit", "purchase": "debit", "outflow": "debit", "dr": "debit", "income": "credit", "deposit": "credit", "receipt": "credit", "inflow": "credit", "cr": "credit"})
    df["amount"] = df["amount"].fillna(0).abs()

    desc_col = next((c for c in ["description", "merchant", "narration", "details", "particulars"] if c in df.columns), None)
    if desc_col is None:
        df["description"] = "Unknown"
        desc_col = "description"
    df["merchant"] = df[desc_col].fillna("Unknown").astype(str).str.strip().str.title()
    df = df.dropna(subset=["date", "amount"]).sort_values("date").reset_index(drop=True)
    keep = ["date", "merchant", "amount", "type"] + (["true_category"] if "true_category" in df.columns else [])
    return df[keep]

# ---- Agent 2: Categorization (rules + learning from user corrections) ---------
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

def _spend(df): return df[(df.type=="debit")&(df.category!="Investments")]

# ---- Agent 3: Spending Pattern Analysis -------------------------------------
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

# ---- Agent 4: Budget Management (50/30/20 + adaptive category caps) ---------
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

# ---- Agent 5: Financial Health Score ----------------------------------------
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

# ---- Agent 6: Anomaly Detection ---------------------------------------------
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

# ---- Agent 7: Subscription Intelligence -------------------------------------
def analyze_subscriptions(df,last_used,today):
    s=df[(df.category=="Subscriptions")&(df.type=="debit")]; out=[]
    for m,x in s.groupby("merchant"):
        amt=x.amount.mode().iloc[0]; lu=pd.to_datetime(last_used.get(m,today)); idle=(today-lu).days/30
        out.append(dict(merchant=m,monthly=amt,months_seen=x.month.nunique(),idle_months=round(idle,1),annual=amt*12,unused=idle>=3,action="Cancel" if idle>=3 else "Keep"))
    return out

# ---- Agent 8: Cash-Flow Forecast (day-by-day simulation) --------------------
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

# ---- Agent 9: Financial Advisor ---------------------------------------------
def advise(state):
    r=[]; sp=state["spending"]; h=state["health"]; df=state["df"]
    for i in sp["insights"]:
        if i["type"]=="trend" and i["category"]=="Food & Dining":
            f=df[(df.category=="Food & Dining")&df.merchant.isin(["Swiggy","Zomato","Dominos"])]; aov=f.amount.mean() if len(f) else 400
            r.append(dict(title="Cut 2 restaurant/delivery orders a week",saving=round(2*aov*52),why=i["text"]))
        elif i["type"]=="trend": r.append(dict(title=f"Set a cap on {i['category']}",saving=round(0.1*sp["monthly"][i["category"]].iloc[-1]*12),why=i["text"]))
    for i in sp["insights"]:
        if i["type"]=="spike": r.append(dict(title=f"Investigate {i['category']} spike",saving=round(sp["monthly"][i["category"]].iloc[:-1].mean()*0+(sp["monthly"][i["category"]].iloc[-1]-sp["monthly"][i["category"]].iloc[:-1].mean())),why=i["text"]))
    un=[s for s in state["subs"] if s["unused"]]
    if un: r.append(dict(title="Cancel unused subscriptions: "+", ".join(s["merchant"] for s in un),saving=round(sum(s["annual"] for s in un)),why=f"{len(un)} subscription(s) idle for 3+ months."))
    if h["emergency_months"]<6: r.append(dict(title=f"Build emergency fund to 6 months (now {h['emergency_months']:.1f})",saving=0,why="Emergency fund below the 6-month target."))
    if h["savings_rate"]<.2: r.append(dict(title="Raise savings rate to 20%",saving=round((0.2-h["savings_rate"])*state["income"]*12),why=f"Savings rate is {h['savings_rate']:.0%}."))
    return r

def llm_narrate(state):
    rag_ctx = build_rag_context(state)
    facts = "\n".join(f"- {item.get('title', 'Financial rule')}: {item.get('content', '')}" for item in rag_ctx["facts"])
    summary_data = {
        "score": state["health"]["score"],
        "income": state["income"],
        "savings_rate": state["health"]["savings_rate"],
        "emergency_months": state["health"]["emergency_months"],
        "min_balance": state["forecast"]["min_balance"],
        "top_alerts": [a["text"] for a in state["alerts"][:4]],
        "top_recommendations": [r["title"] for r in state["advice"][:4]],
    }
    prompt = (
        "Return valid JSON only with keys: summary, risk_level, key_actions, confidence. "
        "The summary should be 2-4 sentences, risk_level should be one of LOW/MEDIUM/HIGH, "
        "key_actions should be a list of 3 short action items, confidence should be a number between 0 and 1. "
        "Use only the facts below and do not invent unsupported claims.\n\n"
        f"User facts: {json.dumps(summary_data, default=str)}\n\n"
        f"Knowledge base:\n{facts}"
    )
    system_msg = (
        "You are a careful and encouraging financial wellness coach. Keep the tone helpful, concise, and practical. "
        "Do not make investment recommendations or invent unsupported financial claims. Return JSON only."
    )
    raw = groq_chat(prompt, system_msg=system_msg)
    if not raw:
        fallback = {
            "summary": f"Your financial health score is {state['health']['score']}/100. Savings rate is {state['health']['savings_rate']:.0%}, emergency cushion is {state['health']['emergency_months']:.1f} months, and the main risks are {', '.join(a['type'] for a in state['alerts'][:3]) or 'steady spending'}.",
            "risk_level": state["forecast"]["risk"],
            "key_actions": [r["title"] for r in state["advice"][:3]],
            "confidence": 0.85,
        }
        return fallback
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {
        "summary": raw,
        "risk_level": state["forecast"]["risk"],
        "key_actions": [r["title"] for r in state["advice"][:3]],
        "confidence": 0.8,
    }

# ---- Agent 10: Alert & Notification -----------------------------------------
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

# ---- Advanced: Goal planner, Life-event simulation, Financial Twin, Readiness ---
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
