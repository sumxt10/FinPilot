"""Public agent API for FinPilot.

Each role has a dedicated module; this package keeps the original import
surface (``import agents as A``) stable for the UI, evaluation, and tests.
"""

from .ingestion_agent import ingest, parse_pdf_file, parse_pdf_text
from .categorization_agent import categorize
from .spending_agent import analyze_spending
from .budget_agent import plan_budget
from .health_agent import health_score
from .anomaly_agent import detect_anomalies
from .subscriptions_agent import analyze_subscriptions
from .forecast_agent import forecast
from .advisor_agent import advise, llm_narrate
from .notifications_agent import notify
from .orchestrator_agent import review, run_pipeline
from .shared_agent import (
    CATS,
    NEEDS,
    WANTS,
    build_rag_context,
    get_groq_api_key,
    goal_plan,
    groq_chat,
    load_rag_kb,
    readiness,
    retrieve_rag_facts,
    simulate_purchase,
    twin,
)

__all__ = [
    "CATS", "NEEDS", "WANTS", "ingest", "parse_pdf_file", "parse_pdf_text",
    "categorize", "analyze_spending", "plan_budget", "health_score",
    "detect_anomalies", "analyze_subscriptions", "forecast", "advise",
    "llm_narrate", "notify", "review", "run_pipeline", "build_rag_context",
    "get_groq_api_key", "goal_plan", "groq_chat", "load_rag_kb",
    "readiness", "retrieve_rag_facts", "simulate_purchase", "twin",
]
