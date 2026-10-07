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
