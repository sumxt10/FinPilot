# FinPilot – Autonomous Financial Wellness Agent (PS-05, FinTech)
Multi-agent AI system that ingests bank/UPI/card statements, categorizes spending, detects anomalies, tracks budgets, forecasts cash flow and gives proactive advice. UI: Streamlit.

## Run (Windows / VS Code)
```
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python data/generate_data.py
python -m streamlit run app.py
python evaluation/run_eval.py      # metrics for the Results section
```
Optional: set `GROQ_API_KEY` (and `MODEL_NAME`) to add an LLM-written summary. Without it everything works deterministically.

## Data
`data/transactions.csv` (+`profile.json`) is synthetic: 12 months with a richer income and spending pattern, duplicate charges, idle subscriptions, and suspicious payments. Upload your own CSV/JSON/PDF in the sidebar (columns: date, description, amount, type — or separate debit/credit columns). Text-based PDF bank and card statements are normalized automatically before analysis.

## Groq API key setup
Use one of these options:

1. Project root `.env` file
```
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Copy `.env.example` to `.env` and add your local key. The `.gitignore`
protects `.env` and Streamlit secrets from accidental Git commits. Never
paste a real API key into source files, README examples, screenshots, or
issue reports. If a key has already been exposed, revoke it and create a new
one before pushing to GitHub.

2. Streamlit secrets file
Create `.streamlit/secrets.toml`:
```
GROQ_API_KEY = "your_key_here"
GROQ_MODEL = "llama-3.3-70b-versatile"
```

The app reads the key from `.env` first, then falls back to `st.secrets` when running in Streamlit.

## RAG usage inside the system
This project already uses a lightweight RAG flow in `agents.py`:
- `load_rag_kb()` loads domain knowledge from `docs/financial_kb.json`
- `retrieve_rag_facts()` scores the best matching financial guidance for the user’s current state
- `build_rag_context()` creates a context from income, savings rate, emergency cushion, top spending category, and the current alerts
- `llm_narrate()` sends the retrieved facts plus the user financial snapshot to Groq for a grounded summary

This is the ideal place for RAG because it grounds the LLM in financial rules and user-specific metrics rather than free-form advice.

## Agents (`agents/`)

Each role is now isolated in its own module instead of a single `agents.py`
file. `agents/__init__.py` keeps the existing public API stable while the
orchestrator composes the roles:
| # | Agent | Job |
|---|---|---|
| 1 | `agents/ingestion_agent.py` | Normalize CSV/JSON/PDF to date/merchant/amount/type |
| 2 | `agents/categorization_agent.py` | Boundary-aware keyword rules + user corrections |
| 3 | Spending Analysis | Monthly pivots, trend (3-month rise) and spike detection |
| 4 | Budget Management | 50/30/20 buckets + adaptive category caps |
| 5 | Financial Health | Score /100: savings rate, debt ratio, consistency, emergency fund |
| 6 | Anomaly Detection | Robust z-score fraud flags, duplicate charges |
| 7 | Subscription Intelligence | Recurring charges, idle months, annual saving |
| 8 | Cash-Flow Forecast | 25-day day-by-day simulation of bills, salary, variable spend |
| 9 | Financial Advisor | Quantified recommendations (₹/year) |
| 10 | Alert & Notification | Severity-ranked alerts with channel |
| 11 | `agents/orchestrator_agent.py` | Planner → Executor agents → Reviewer guardrail, with trace |

The remaining role files follow the same `*_agent.py` naming convention;
`shared.py` contains common constants and implementation helpers.

Advanced: goal planning, car-purchase simulation, Financial Twin (job loss / raise / loan), investment readiness.

## MCP integration

`mcp_server.py` exposes two MCP-compatible JSON-RPC tools over stdin/stdout:

- `finpilot_normalize_transactions`
- `finpilot_analyze_transactions`

The tools return canonical transaction data or a traceable analysis summary
with health, alerts, advice, and retrieved RAG context. The Streamlit UI and
MCP server share the same deterministic agent pipeline, so results remain
consistent and the UI still works without an API key.

Run the server for an MCP client with:

```
python mcp_server.py
```

## Architecture
Upload → Orchestrator plan → Ingest → Categorize → Analyze → Budget → Health → Anomaly → Subscriptions → Forecast → Advise → Notify → Reviewer → Streamlit dashboard + Agent Trace. LLM (optional) only narrates; all numbers come from deterministic tools, so nothing is hallucinated.

## Lab experiment mapping
E1 structured I/O, trace logs, reviewer · E2 rule-based financial decisions · E3 tool agents with fallback (LLM optional) · E4 traceable evidence per advice · E5 decompose→analyze→compare pipeline · E6 tool-style agent functions (MCP-ready) · E7 rule-based scoring/alerts · E8 alert escalation · E9 multi-agent delegation via orchestrator · E10 full Planner-Reviewer system with observability + Streamlit.

## Report skeleton
1 Problem/Scope/Users/Dataset · 2 Literature review (≥10 papers: LLM agents, tool use, anomaly detection, forecasting, personal-finance AI, HITL, safety) · 3 CSD + methodology (ingestion, preprocessing, architecture, classification, visuals) · 4 Technology (Python, Streamlit, Pandas, NumPy, Plotly, optional Groq) · 5 Implementation · 6 Results (run `evaluation/run_eval.py`).
