import re
from typing import Any


AGENT_ID = "sql_agent_real_001"


def normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip()).rstrip(";").strip()


def validate_generated_sql(sql_query: Any) -> dict:
    """
    Conservative local validation for HEAAP Phase 18.3.

    This is not a complete SQL parser or a database authorization
    mechanism. It rejects unsupported or suspicious statements.

    No SQL is executed.
    """

    if not isinstance(sql_query, str):
        return {
            "status": "error",
            "error_code": "INVALID_INPUT",
            "message": "sql_query must be a string",
            "validation_passed": False,
        }

    if not sql_query.strip():
        return {
            "status": "error",
            "error_code": "INVALID_INPUT",
            "message": "sql_query cannot be empty",
            "validation_passed": False,
        }

    if len(sql_query) > 10000:
        return {
            "status": "error",
            "error_code": "INVALID_INPUT",
            "message": "sql_query exceeds maximum length",
            "validation_passed": False,
        }

    sql = normalize_sql(sql_query)

    if not sql.upper().startswith("SELECT "):
        return {
            "status": "error",
            "error_code": "UNSAFE_SQL",
            "message": "Only SELECT queries are supported",
            "validation_passed": False,
        }

    if ";" in sql or "--" in sql or "/*" in sql or "*/" in sql:
        return {
            "status": "error",
            "error_code": "UNSAFE_SQL",
            "message": "Multiple statements and SQL comments are not allowed",
            "validation_passed": False,
        }

    forbidden = (
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
        "TRUNCATE", "MERGE", "CREATE", "GRANT",
        "REVOKE", "EXEC", "EXECUTE",
    )

    for keyword in forbidden:
        if re.search(rf"\b{keyword}\b", sql, re.IGNORECASE):
            return {
                "status": "error",
                "error_code": "UNSAFE_SQL",
                "message": f"Forbidden SQL keyword: {keyword}",
                "validation_passed": False,
            }

    return {
        "status": "success",
        "error_code": None,
        "message": "SQL passed preliminary local safety checks",
        "validation_passed": True,
        "sql_query": sql,
        "database_executed": False,
    }
