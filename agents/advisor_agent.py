from __future__ import annotations

"""Financial Advisor Agent and grounded narration."""
import json

from .shared_agent import build_rag_context, groq_chat

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
