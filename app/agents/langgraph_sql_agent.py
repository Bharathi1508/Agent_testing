"""
HEAAP Phase 17.3
Local LangGraph SQL Agent demonstration.

No LLM, database access, or actual SQL execution.
"""

from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END


class SQLAgentState(TypedDict, total=False):
    payload: dict[str, Any]
    response: dict[str, Any]


def process_request(state: SQLAgentState) -> dict:
    payload = state.get("payload", {})

    if not isinstance(payload, dict):
        return {
            "response": {
                "status": "rejected",
                "error_code": "INVALID_INPUT",
                "message": "Payload must be an object",
            }
        }

    action = payload.get("action")

    if not isinstance(action, str) or not action:
        return {
            "response": {
                "status": "rejected",
                "error_code": "INVALID_INPUT",
                "message": "Action must be a non-empty string",
            }
        }

    if action not in ("generate_sql", "validate_sql"):
        return {
            "response": {
                "status": "rejected",
                "error_code": "INVALID_ACTION",
                "message": "Unsupported action",
            }
        }

    required_field = (
        "question"
        if action == "generate_sql"
        else "sql_query"
    )

    value = payload.get(required_field)

    if not isinstance(value, str) or not value.strip():
        return {
            "response": {
                "status": "rejected",
                "error_code": "INVALID_INPUT",
                "message": (
                    f"{required_field} must be a "
                    "non-empty string"
                ),
            }
        }

    if action == "generate_sql":
        result = {
            "sql": "SELECT 1 AS demonstration_result",
            "demonstration": True,
        }
    else:
        result = {
            "valid": True,
            "demonstration": True,
        }

    return {
        "response": {
            "status": "success",
            "agent_id": "sql_agent_001",
            "action": action,
            "result": result,
        }
    }


def create_sql_graph():
    builder = StateGraph(SQLAgentState)
    builder.add_node("process_request", process_request)
    builder.add_edge(START, "process_request")
    builder.add_edge("process_request", END)
    return builder.compile()


sql_graph = create_sql_graph()
