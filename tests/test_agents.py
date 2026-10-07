import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import agents as A
from mcp_server import handle_request


def test_ingest_handles_currency_strings():
    df = pd.DataFrame(
        {
            "date": ["2026-02-01", "2026-02-02"],
            "description": ["Swiggy", "Salary"],
            "amount": ["₹1,200.00", "₹25,000.00"],
            "type": ["debit", "credit"],
        }
    )

    cleaned = A.ingest(df)

    assert list(cleaned["merchant"]) == ["Swiggy", "Salary"]
    assert list(cleaned["amount"]) == [1200.0, 25000.0]
    assert list(cleaned["type"]) == ["debit", "credit"]


def test_categorization_does_not_match_jio_inside_ajio():
    categorized = A.categorize(A.ingest([
        {"date": "2026-02-01", "description": "Ajio", "amount": 800, "type": "debit"},
    ]))

    assert categorized.loc[0, "category"] == "Shopping"


def test_run_pipeline_handles_wrapped_json_transactions():
    payload = {
        "transactions": [
            {"date": "2026-02-01", "description": "Grocery", "amount": 1200, "type": "debit"},
            {"date": "2026-02-02", "description": "Salary", "amount": 25000, "type": "credit"},
        ]
    }

    state = A.run_pipeline(payload, {"monthly_income": 50000, "opening_balance": 100000})

    assert len(state["df"]) == 2
    assert state["budget"]["month"] == "2026-02"
    assert state["budget"]["buckets"]["wants"]["spent"] == 1200


def test_run_pipeline_handles_fi_bank_statement_json():
    payload = {
        "Account": {
            "Transactions": {
                "Transaction": [
                    {
                        "type": "DEBIT",
                        "amount": "100.0",
                        "transactionTimestamp": "2024-05-29T09:00:00+05:30",
                        "valueDate": "2024-05-29",
                        "narration": "SHOP PAYMENT",
                    },
                    {
                        "type": "CREDIT",
                        "amount": "25000.0",
                        "transactionTimestamp": "2024-05-30T10:00:00+05:30",
                        "valueDate": "2024-05-30",
                        "narration": "SALARY",
                    },
                ]
            }
        }
    }

    state = A.run_pipeline(payload, {"monthly_income": 50000, "opening_balance": 2000})

    assert len(state["df"]) == 2
    assert list(state["df"]["type"]) == ["debit", "credit"]
    assert state["df"]["date"].dt.tz is None
    assert state["forecast"]["series"].shape[0] == 25


def test_run_pipeline_normalizes_common_json_transaction_types():
    payload = {
        "data": [
            {"transaction_date": "2026-02-01", "description": "Grocery", "amount": 1200, "transaction_type": "expense"},
            {"transactionDate": "2026-02-02", "description": "Salary", "amount": 25000, "transaction_type": "income"},
        ]
    }

    state = A.run_pipeline(payload, {"monthly_income": 50000, "opening_balance": 100000})

    assert list(state["df"]["type"]) == ["debit", "credit"]
    assert state["budget"]["buckets"]["wants"]["spent"] == 1200


def test_run_pipeline_handles_credit_only_statement():
    payload = {
        "transactions": [
            {"date": "2026-02-02", "description": "Salary", "amount": 25000, "type": "credit"}
        ]
    }

    state = A.run_pipeline(payload, {"monthly_income": 50000, "opening_balance": 100000})

    assert state["health"]["score"] == 0
    assert state["health"]["avg_spend"] == 0
    assert pd.notna(state["health"]["savings_rate"])
    assert state["health"]["has_spending_data"] is False


def test_ingest_handles_json_transaction_lists():
    cleaned = A.ingest(
        [{"date": "2026-02-01", "description": "Grocery", "amount": 1200, "type": "debit"}]
    )

    assert len(cleaned) == 1
    assert cleaned.loc[0, "date"] == pd.Timestamp("2026-02-01")
    assert cleaned.loc[0, "type"] == "debit"


def test_parse_pdf_text_extracts_transactions():
    sample = """
    Statement
    01-Feb-2026, SWIGGY, -₹1,200.00
    02-Feb-2026, SALARY, ₹25,000.00
    03-Feb-2026, NETFLIX, -₹649.00
    """

    rows = A.parse_pdf_text(sample)

    assert len(rows) >= 3
    assert any(r["merchant"].lower() == "swiggy" for r in rows)
    assert any(r["merchant"].lower() == "netflix" for r in rows)


def test_mcp_lists_finpilot_tools():
    response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == {
        "finpilot_normalize_transactions",
        "finpilot_analyze_transactions",
    }


def test_mcp_analyze_tool_returns_traceable_summary():
    response = handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "finpilot_analyze_transactions",
            "arguments": {
                "transactions": [
                    {"date": "2026-02-01", "description": "Salary", "amount": 25000, "type": "credit"},
                    {"date": "2026-02-02", "description": "Swiggy", "amount": 1200, "type": "debit"},
                ],
                "profile": {"monthly_income": 25000, "opening_balance": 100000},
            },
        },
    })

    result = response["result"]["content"][0]["json"]
    assert result["summary"]["transaction_count"] == 2
    assert 0 <= result["summary"]["health_score"] <= 100
    assert result["trace"][0]["agent"] == "Master Orchestrator (Planner)"
