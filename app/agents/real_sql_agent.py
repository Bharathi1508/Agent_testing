"""
HEAAP Phase 18.1
Real deterministic LangGraph SQL Agent.

- Supports a small allowlist of insurance questions
- Uses only approved SQL templates
- Validates generated SQL
- Does not connect to a database
- Does not execute SQL
- Preserves the existing Phase 17 demonstration agent
"""

import re
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END


# IMPORTANT:
# These are example logical tables for local development.
# They are NOT verified against your Databricks catalog.
#
# Before any future database execution, replace these
# with reviewed, fully qualified tables and column names.

TABLE_COLUMNS = {
    "policies": {
        "policy_id",
        "policy_type",
        "annual_premium",
    },
    "claims": {
        "claim_id",
        "policy_id",
        "reported_amount",
        "approved_amount",
    },
}


SQL_TEMPLATES = {
    "total annual premium": (
        "SELECT SUM(annual_premium) AS total_annual_premium "
        "FROM policies"
    ),
    "total number of policies": (
        "SELECT COUNT(*) AS total_policies "
        "FROM policies"
    ),
    "total number of claims": (
        "SELECT COUNT(*) AS total_claims "
        "FROM claims"
    ),
    "average annual premium": (
        "SELECT AVG(annual_premium) AS average_annual_premium "
        "FROM policies"
    ),
    "total reported claim amount": (
        "SELECT SUM(reported_amount) AS total_reported_amount "
        "FROM claims"
    ),
    "total approved claim amount": (
        "SELECT SUM(approved_amount) AS total_approved_amount "
        "FROM claims"
    ),
}


class SQLAgentState(TypedDict, total=False):
    question: Any
    normalized_question: str
    sql_query: str
    status: str
    error_code: str | None
    message: str
    validation_passed: bool


def reject(state, code, message):
    return {
        "status": "rejected",
        "error_code": code,
        "message": message,
        "sql_query": "",
        "validation_passed": False,
    }


def validate_input(state: SQLAgentState):

    question = state.get("question")

    if not isinstance(question, str):
        return reject(
            state,
            "INVALID_INPUT",
            "Question must be a string",
        )

    question = question.strip()

    if not question:
        return reject(
            state,
            "INVALID_INPUT",
            "Question cannot be empty",
        )

    if len(question) > 500:
        return reject(
            state,
            "INVALID_INPUT",
            "Question exceeds length limit",
        )

    normalized = re.sub(
        r"\s+",
        " ",
        question.lower(),
    ).strip()

    return {
        "normalized_question": normalized,
        "status": "validated",
        "error_code": None,
        "message": "Input accepted",
    }


def generate_sql(state: SQLAgentState):

    question = state["normalized_question"]

    sql = SQL_TEMPLATES.get(question)

    if sql is None:
        return reject(
            state,
            "UNSUPPORTED_QUESTION",
            "Question is not supported by the SQL templates",
        )

    return {
        "sql_query": sql,
        "status": "generated",
        "error_code": None,
        "message": "SQL generated",
    }


def validate_generated_sql(state: SQLAgentState):

    sql = state.get("sql_query", "")

    if not isinstance(sql, str) or not sql:
        return reject(
            state,
            "SQL_VALIDATION_FAILED",
            "SQL is missing",
        )

    # Exact template membership prevents arbitrary SQL from
    # being accepted by this limited implementation.
    if sql not in SQL_TEMPLATES.values():
        return reject(
            state,
            "SQL_VALIDATION_FAILED",
            "SQL is not an approved template",
        )

    # Defensive checks; the exact allowlist above is
    # the primary enforcement mechanism.
    if not sql.upper().startswith("SELECT "):
        return reject(
            state,
            "SQL_VALIDATION_FAILED",
            "Only SELECT queries are allowed",
        )

    if any(token in sql for token in (";", "--", "/*", "*/")):
        return reject(
            state,
            "SQL_VALIDATION_FAILED",
            "SQL contains prohibited syntax",
        )

    return {
        "status": "success",
        "error_code": None,
        "message": "SQL generated and validated",
        "validation_passed": True,
    }


def route_after_input(state: SQLAgentState):
    if state.get("status") == "rejected":
        return "end"
    return "generate"


def route_after_generation(state: SQLAgentState):
    if state.get("status") == "rejected":
        return "end"
    return "validate"


def build_sql_graph():

    workflow = StateGraph(SQLAgentState)

    workflow.add_node("input_validation", validate_input)
    workflow.add_node("sql_generation", generate_sql)
    workflow.add_node("sql_validation", validate_generated_sql)

    workflow.set_entry_point("input_validation")

    workflow.add_conditional_edges(
        "input_validation",
        route_after_input,
        {
            "generate": "sql_generation",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "sql_generation",
        route_after_generation,
        {
            "validate": "sql_validation",
            "end": END,
        },
    )

    workflow.add_edge("sql_validation", END)

    return workflow.compile()


real_sql_graph = build_sql_graph()


def run_sql_agent(question):

    result = real_sql_graph.invoke({
        "question": question,
    })

    return {
        "agent_id": "sql_agent_real_001",
        "status": result.get("status", "error"),
        "error_code": result.get("error_code"),
        "message": result.get("message", ""),
        "sql_query": result.get("sql_query", ""),
        "validation_passed": result.get(
            "validation_passed", False
        ),
        "execution_target": "langgraph_local",
        "database_executed": False,
    }
