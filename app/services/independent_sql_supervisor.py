import os
import re
import sqlparse

from app.services.heaap_sql_assurance import parse_schema_explorer_question
from app.services.metadata_service import get_columns, list_tables


def _identifier(value):
    if not isinstance(value, str):
        raise ValueError("Invalid identifier")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError("Invalid identifier")
    return f"`{value}`"


def _supervise_schema_analytical_query(sql, selection, intent):
    selected_table = selection.get("primary_table")
    required_columns = {
        str(column).lower() for column in intent["required_columns"]
    }
    selected_columns = {
        str(column).lower()
        for column in selection.get("selected_columns", [])
    }
    checks = {
        "supported_business_intent": True,
        "metadata_table_alignment": (
            isinstance(selected_table, str)
            and selected_table.lower() == intent["table"].lower()
        ),
        "metadata_required_columns": required_columns.issubset(
            selected_columns
        ),
        "metadata_column_minimality": required_columns == selected_columns,
        "no_sql_comments": not bool(
            re.search(r"--|/\*|\*/|#", sql)
        ),
    }
    details = {}

    statements = sqlparse.parse(sql)
    checks["single_select"] = (
        len(statements) == 1
        and statements[0].get_type() == "SELECT"
    )
    checks["no_extra_statements"] = len(statements) == 1

    try:
        catalog = _identifier(os.environ["DATABRICKS_CATALOG"])
        schema = _identifier(os.environ["DATABRICKS_SCHEMA"])
        table = _identifier(intent["table"])
        available_tables = set()
        for item in list_tables():
            if isinstance(item, str):
                available_tables.add(item.lower())
            elif isinstance(item, dict):
                name = item.get("table_name") or item.get("name")
                if isinstance(name, str):
                    available_tables.add(name.lower())
        checks["live_table_exists"] = (
            intent["table"].lower() in available_tables
        )

        live_columns = (
            {
                str(column["column_name"]).lower(): str(
                    column.get("data_type") or ""
                ).upper()
                for column in get_columns(intent["table"])
            }
            if checks["live_table_exists"]
            else {}
        )
        checks["live_required_columns"] = required_columns.issubset(
            live_columns
        )

        dimension = intent.get("dimension")
        if dimension:
            checks["supported_dimension_type"] = bool(
                re.match(
                    r"^(STRING|CHAR|VARCHAR|BOOLEAN|DATE|TIMESTAMP|"
                    r"TINYINT|SMALLINT|INT|INTEGER|BIGINT|LONG|FLOAT|DOUBLE|"
                    r"DECIMAL|NUMERIC)\b",
                    live_columns.get(dimension.lower(), ""),
                )
            )
        measure = intent.get("measure")
        if measure:
            checks["numeric_measure_type"] = bool(
                re.match(
                    r"^(TINYINT|SMALLINT|INT|INTEGER|BIGINT|LONG|FLOAT|"
                    r"DOUBLE|DECIMAL|NUMERIC)\b",
                    live_columns.get(measure.lower(), ""),
                )
            )
        details["live_schema_columns"] = sorted(live_columns)

        relation = f"{catalog}.{schema}.{table}"
        if intent["query_type"] == "count_all":
            expected_sql = (
                f"SELECT COUNT(*) AS `record_count` FROM {relation} LIMIT 100"
            )
        elif intent["query_type"] == "count_by_dimension":
            quoted_dimension = _identifier(intent["dimension"])
            expected_sql = (
                f"SELECT {quoted_dimension}, COUNT(*) AS `record_count` "
                f"FROM {relation} GROUP BY {quoted_dimension} "
                f"ORDER BY {quoted_dimension} LIMIT 100"
            )
        elif intent["query_type"] == "average":
            measure = _identifier(intent["measure"])
            alias = _identifier(f"average_{intent['measure']}")
            expected_sql = (
                f"SELECT AVG({measure}) AS {alias} "
                f"FROM {relation} LIMIT 100"
            )
        elif intent["query_type"] == "average_by_dimension":
            quoted_dimension = _identifier(intent["dimension"])
            measure = _identifier(intent["measure"])
            alias = _identifier(f"average_{intent['measure']}")
            expected_sql = (
                f"SELECT {quoted_dimension}, AVG({measure}) AS {alias} "
                f"FROM {relation} GROUP BY {quoted_dimension} "
                f"ORDER BY {quoted_dimension} LIMIT 100"
            )
        else:
            measure = _identifier(intent["measure"])
            minimum = _identifier(f"minimum_{intent['measure']}")
            maximum = _identifier(f"maximum_{intent['measure']}")
            expected_sql = (
                f"SELECT MIN({measure}) AS {minimum}, "
                f"MAX({measure}) AS {maximum} "
                f"FROM {relation} LIMIT 100"
            )
        checks["approved_sql_structure"] = bool(
            re.fullmatch(
                re.escape(expected_sql) + r"\s*;?",
                sql.strip(),
                re.IGNORECASE,
            )
        )
    except Exception as exc:
        checks["live_table_exists"] = False
        checks["live_required_columns"] = False
        checks["approved_sql_structure"] = False
        details["schema_error"] = str(exc)

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "details": details,
        "execution_allowed": status == "PASS",
        "note": (
            "Independent live-schema, measure-type, and exact-template checks "
            "for a bounded read-only analytical query."
        ),
    }

def supervise_sql(question, sql, selection):
    checks = {}
    details = {}

    if not isinstance(sql, str) or not sql.strip():
        return {
            "status": "REVIEW",
            "checks": {},
            "details": {"reason": "No generated SQL"},
            "execution_allowed": False,
        }

    schema_intent = parse_schema_explorer_question(question)
    if schema_intent:
        return _supervise_schema_analytical_query(
            sql,
            selection,
            schema_intent,
        )

    statements = sqlparse.parse(sql)
    checks["single_select"] = (
        len(statements) == 1
        and statements[0].get_type() == "SELECT"
    )

    # Phase 11 deliberately supports one approved business intent.
    normalized_question = " ".join(question.lower().split())

    checks["supported_business_intent"] = (
        "overdue" in normalized_question
        and "loan" in normalized_question
        and (
            "customer" in normalized_question
            or "installment" in normalized_question
        )
    )

    expected_table = "gold_loan_portfolio_summary"
    required_columns = {
        "customer_id",
        "loan_id",
        "overdue_installments",
    }

    checks["metadata_table_alignment"] = (
        selection.get("primary_table") == expected_table
    )

    try:
        catalog = _identifier(os.environ["DATABRICKS_CATALOG"])
        schema = _identifier(os.environ["DATABRICKS_SCHEMA"])
        table = _identifier(expected_table)

        expected_relation = f"{catalog}.{schema}.{table}"

        # Independently fetch the live schema instead of trusting
        # the selected column list returned by the metadata agent.
        available_tables = set()
        for item in list_tables():
            if isinstance(item, str):
                available_tables.add(item)
            elif isinstance(item, dict):
                name = (
                    item.get("table_name")
                    or item.get("name")
                )
                if isinstance(name, str):
                    available_tables.add(name)

        checks["live_table_exists"] = (
            expected_table in available_tables
        )

        if checks["live_table_exists"]:
            live_columns = {
                column["column_name"]
                for column in get_columns(expected_table)
            }
        else:
            live_columns = set()

        checks["live_required_columns"] = (
            required_columns.issubset(live_columns)
        )

        details["live_schema_columns"] = sorted(live_columns)

    except Exception as exc:
        expected_relation = None
        checks["live_table_exists"] = False
        checks["live_required_columns"] = False
        details["schema_error"] = str(exc)

    # Strict allowlist: accept only the independently approved
    # SQL structure for this specific business question.
    pattern = (
        r"^\s*SELECT\s+"
        r"customer_id\s*,\s*"
        r"loan_id\s*,\s*"
        r"overdue_installments\s+"
        r"FROM\s+"
        + re.escape(expected_relation or "__INVALID_RELATION__")
        + r"\s+WHERE\s+"
        r"overdue_installments\s*>\s*0\s+"
        r"LIMIT\s+100\s*;?\s*$"
    )

    checks["approved_sql_structure"] = bool(
        re.fullmatch(pattern, sql, flags=re.IGNORECASE)
    )

    checks["no_sql_comments"] = not bool(
        re.search(r"--|/\*|\*/|#", sql)
    )

    checks["no_extra_statements"] = (
        len(statements) == 1
    )

    if all(checks.values()):
        status = "PASS"
    else:
        status = "FAIL"

    return {
        "status": status,
        "checks": checks,
        "details": details,
        "execution_allowed": False,
        "note": (
            "Independent SQL template and live-schema validation. "
            "Databricks execution remains disabled pending "
            "semantic approval and execution security controls."
        ),
    }
