
from app.services.sql_generator import generate_top_loans_sql
from app.services.sql_validator import validate_sql
from app.adapters.databricks_client import execute_query


def sql_agent(state):
    action = state.get("action")

    if action != "top_loans":
        return {
            "status": "unsupported",
            "result": "Unknown SQL operation"
        }

    query = generate_top_loans_sql(
        table_name=state["table_name"],
        limit=state.get("limit", 5)
    )

    validate_sql(query)

    # Execute using the existing Databricks client
    rows = execute_query(query)

    return {
        "status": "success",
        "sql": query,
        "result": rows
    }
