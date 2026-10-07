"""Model Context Protocol bridge for FinPilot.

The server uses MCP's JSON-RPC-over-stdio shape without requiring an
additional runtime dependency. It exposes safe, deterministic finance tools
for an MCP client, while the Streamlit app continues to work offline.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable

import pandas as pd

from agents import build_rag_context, ingest, run_pipeline


Tool = Callable[[dict[str, Any]], dict[str, Any]]


def _json_safe(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def analyze_transactions(arguments: dict[str, Any]) -> dict[str, Any]:
    """Run the complete deterministic agent workflow on transaction records."""
    records = arguments.get("transactions")
    if not isinstance(records, (list, dict)):
        raise ValueError("transactions must be a list or a wrapped transaction object")
    profile = arguments.get("profile") or {}
    state = run_pipeline(records, profile, arguments.get("overrides"))
    return _json_safe({
        "summary": {
            "transaction_count": len(state["df"]),
            "health_score": state["health"]["score"],
            "cash_flow_risk": state["forecast"]["risk"],
            "alert_count": len(state["alerts"]),
        },
        "health": state["health"],
        "alerts": state["alerts"],
        "advice": state["advice"],
        "trace": state["trace"],
        "rag_context": build_rag_context(state),
    })


def normalize_transactions(arguments: dict[str, Any]) -> dict[str, Any]:
    """Normalize records into the canonical date/merchant/amount/type schema."""
    records = arguments.get("transactions")
    if records is None:
        raise ValueError("transactions is required")
    return _json_safe(ingest(records))


TOOLS: dict[str, Tool] = {
    "finpilot_normalize_transactions": normalize_transactions,
    "finpilot_analyze_transactions": analyze_transactions,
}


def _response(request_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        response["error"] = error
    else:
        response["result"] = result
    return response


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        return _response(request_id, {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "finpilot", "version": "1.0.0"},
        })
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _response(request_id, {"tools": [
            {"name": name, "description": tool.__doc__ or "", "inputSchema": {"type": "object"}}
            for name, tool in TOOLS.items()
        ]})
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        if name not in TOOLS:
            return _response(request_id, error={"code": -32602, "message": f"Unknown tool: {name}"})
        try:
            result = TOOLS[name](params.get("arguments") or {})
            return _response(request_id, {"content": [{"type": "json", "json": result}]})
        except (TypeError, ValueError, KeyError) as exc:
            return _response(request_id, error={"code": -32602, "message": str(exc)})
    return _response(request_id, error={"code": -32601, "message": f"Unknown method: {method}"})


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, default=str) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
