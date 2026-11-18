import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import sqlparse

from app.services.metadata_service import get_columns
from app.services.sql_generator import quote_identifier


SCHEMA_ANALYTICAL_QUERY_TYPES = frozenset({
    "count_all",
    "count_by_dimension",
    "average",
    "average_by_dimension",
    "min_max",
})

_SCALAR_TYPE_PATTERN = (
    r"^(STRING|CHAR|VARCHAR|BOOLEAN|DATE|TIMESTAMP|"
    r"TINYINT|SMALLINT|INT|INTEGER|BIGINT|LONG|FLOAT|DOUBLE|"
    r"DECIMAL|NUMERIC)\b"
)
_NUMERIC_TYPE_PATTERN = (
    r"^(TINYINT|SMALLINT|INT|INTEGER|BIGINT|LONG|FLOAT|DOUBLE|"
    r"DECIMAL|NUMERIC)\b"
)


def parse_schema_explorer_question(
    question: str,
) -> dict[str, Any] | None:
    normalized = " ".join(question.strip().rstrip("?").split())
    patterns = (
        (
            "count_by_dimension",
            r"how many records are there by "
            r"(?P<dimension>[A-Za-z_][A-Za-z0-9_]*) in "
            r"(?P<table>gold_[A-Za-z0-9_]*)",
        ),
        (
            "count_by_dimension",
            r"show records by "
            r"(?P<dimension>[A-Za-z_][A-Za-z0-9_]*) in "
            r"(?P<table>gold_[A-Za-z0-9_]*)",
        ),
        (
            "count_all",
            r"how many records are in "
            r"(?P<table>gold_[A-Za-z0-9_]*)",
        ),
        (
            "average_by_dimension",
            r"what is the average "
            r"(?P<measure>[A-Za-z_][A-Za-z0-9_]*) by "
            r"(?P<dimension>[A-Za-z_][A-Za-z0-9_]*) in "
            r"(?P<table>gold_[A-Za-z0-9_]*)",
        ),
        (
            "average",
            r"what is the average "
            r"(?P<measure>[A-Za-z_][A-Za-z0-9_]*) in "
            r"(?P<table>gold_[A-Za-z0-9_]*)",
        ),
        (
            "min_max",
            r"what is the minimum and maximum "
            r"(?P<measure>[A-Za-z_][A-Za-z0-9_]*) in "
            r"(?P<table>gold_[A-Za-z0-9_]*)",
        ),
    )
    for query_type, pattern in patterns:
        match = re.fullmatch(pattern, normalized, re.IGNORECASE)
        if match:
            intent: dict[str, Any] = {
                "query_type": query_type,
                "table": match.group("table"),
                "required_columns": [],
            }
            for name in ("dimension", "measure"):
                if match.groupdict().get(name):
                    intent[name] = match.group(name)
                    intent["required_columns"].append(match.group(name))
            return intent
    return None


def parse_schema_count_question(question: str) -> dict[str, str] | None:
    intent = parse_schema_explorer_question(question)
    if intent and intent["query_type"] == "count_by_dimension":
        return {
            "query_type": intent["query_type"],
            "dimension": intent["dimension"],
            "table": intent["table"],
        }
    return None


def _count_by_dimension_sql(intent: dict[str, str]) -> str:
    return _schema_analytical_sql(intent)


def _schema_analytical_sql(intent: dict[str, Any]) -> str:
    catalog = quote_identifier(os.environ["DATABRICKS_CATALOG"])
    schema = quote_identifier(os.environ["DATABRICKS_SCHEMA"])
    table = quote_identifier(intent["table"])
    relation = f"{catalog}.{schema}.{table}"
    query_type = intent["query_type"]

    if query_type == "count_all":
        return (
            f"SELECT COUNT(*) AS `record_count` FROM {relation} LIMIT 100"
        )

    if query_type == "count_by_dimension":
        dimension = quote_identifier(intent["dimension"])
        return (
            f"SELECT {dimension}, COUNT(*) AS `record_count` "
            f"FROM {relation} GROUP BY {dimension} "
            f"ORDER BY {dimension} LIMIT 100"
        )

    measure = quote_identifier(intent["measure"])
    average_alias = quote_identifier(f"average_{intent['measure']}")
    if query_type == "average":
        return (
            f"SELECT AVG({measure}) AS {average_alias} "
            f"FROM {relation} LIMIT 100"
        )

    if query_type == "average_by_dimension":
        dimension = quote_identifier(intent["dimension"])
        return (
            f"SELECT {dimension}, AVG({measure}) AS {average_alias} "
            f"FROM {relation} GROUP BY {dimension} "
            f"ORDER BY {dimension} LIMIT 100"
        )

    if query_type == "min_max":
        minimum_alias = quote_identifier(f"minimum_{intent['measure']}")
        maximum_alias = quote_identifier(f"maximum_{intent['measure']}")
        return (
            f"SELECT MIN({measure}) AS {minimum_alias}, "
            f"MAX({measure}) AS {maximum_alias} "
            f"FROM {relation} LIMIT 100"
        )

    raise ValueError(f"Unsupported schema-derived query type: {query_type}")


def generate_sql(question: str, selection: dict) -> dict[str, Any]:
    """Generate SQL only for bounded, explicitly supported query templates."""

    intent = parse_schema_explorer_question(question)
    if intent:
        table_name = intent["table"]
        selected_table = selection.get("primary_table")
        if (
            not table_name.lower().startswith("gold_")
            or not isinstance(selected_table, str)
            or selected_table.lower() != table_name.lower()
        ):
            return {
                "status": "FAIL",
                "reason": "Question table does not match the selected Gold table",
                "sql": None,
            }

        live_columns = {
            str(column["column_name"]).lower(): str(
                column.get("data_type") or ""
            ).upper()
            for column in get_columns(table_name)
        }
        selected_columns = {
            str(column).lower()
            for column in selection.get("selected_columns", [])
        }
        required_columns = {
            str(column).lower()
            for column in intent["required_columns"]
        }
        missing_live = required_columns - set(live_columns)
        if missing_live:
            return {
                "status": "FAIL",
                "reason": (
                    "Question columns are absent from the live schema: "
                    + ", ".join(sorted(missing_live))
                ),
                "sql": None,
            }
        if not required_columns.issubset(selected_columns):
            return {
                "status": "FAIL",
                "reason": "Question columns are missing from metadata selection",
                "sql": None,
            }

        dimension = intent.get("dimension")
        if dimension and not re.match(
            _SCALAR_TYPE_PATTERN,
            live_columns[dimension.lower()],
        ):
            return {
                "status": "FAIL",
                "reason": "Grouping column must have a supported scalar type",
                "sql": None,
            }

        measure = intent.get("measure")
        if measure and not re.match(
            _NUMERIC_TYPE_PATTERN,
            live_columns[measure.lower()],
        ):
            return {
                "status": "FAIL",
                "reason": "Measure column must have a numeric type",
                "sql": None,
            }

        return {
            "status": "GENERATED",
            "query_type": intent["query_type"],
            "question": question,
            "table": table_name,
            "required_columns": intent["required_columns"],
            "sql": _schema_analytical_sql(intent),
        }

    normalized = " ".join(question.lower().split())

    if not (
        "overdue" in normalized
        and "loan" in normalized
        and ("customer" in normalized or "installment" in normalized)
    ):
        return {
            "status": "REVIEW",
            "reason": "Business question is not supported by this deterministic generator",
            "sql": None,
        }

    table_name = selection.get("primary_table")

    if table_name != "gold_loan_portfolio_summary":
        return {
            "status": "FAIL",
            "reason": "Unexpected table selected",
            "sql": None,
        }

    required = {
        "customer_id",
        "loan_id",
        "overdue_installments",
    }

    selected = set(selection.get("selected_columns", []))

    if not required.issubset(selected):
        return {
            "status": "FAIL",
            "reason": "Required columns missing from metadata selection",
            "sql": None,
        }

    live_columns = {
        column["column_name"]
        for column in get_columns(table_name)
    }

    if not required.issubset(live_columns):
        return {
            "status": "FAIL",
            "reason": "Required columns missing from live schema",
            "sql": None,
        }

    catalog = quote_identifier(os.environ["DATABRICKS_CATALOG"])
    schema = quote_identifier(os.environ["DATABRICKS_SCHEMA"])
    table = quote_identifier(table_name)

    sql = f"""
SELECT
    customer_id,
    loan_id,
    overdue_installments
FROM {catalog}.{schema}.{table}
WHERE overdue_installments > 0
LIMIT 100
""".strip()

    return {
        "status": "GENERATED",
        "sql": sql,
        "table": table_name,
        "required_columns": sorted(required),
        "required_filter": "overdue_installments > 0",
    }


def validate_query_results(
    query_type: str,
    intent: dict[str, Any],
    rows: Any,
) -> dict[str, Any]:
    if query_type == "count_all":
        expected_columns = ["record_count"]
        numeric_columns = {"record_count": "count"}
    elif query_type == "count_by_dimension":
        expected_columns = [intent["dimension"], "record_count"]
        numeric_columns = {"record_count": "count"}
    elif query_type == "average":
        average_column = f"average_{intent['measure']}"
        expected_columns = [average_column]
        numeric_columns = {average_column: "aggregate"}
    elif query_type == "average_by_dimension":
        average_column = f"average_{intent['measure']}"
        expected_columns = [intent["dimension"], average_column]
        numeric_columns = {average_column: "aggregate"}
    elif query_type == "min_max":
        minimum_column = f"minimum_{intent['measure']}"
        maximum_column = f"maximum_{intent['measure']}"
        expected_columns = [minimum_column, maximum_column]
        numeric_columns = {
            minimum_column: "aggregate",
            maximum_column: "aggregate",
        }
    else:
        return {
            "validation_status": "FAIL",
            "checks": {"supported_query_type": "FAIL"},
            "row_count": 0,
        }

    checks = {
        "supported_query_type": "PASS",
        "rows_are_a_list": "PASS" if isinstance(rows, list) else "FAIL",
        "aggregate_row_shape": "PASS",
        "result_row_limit": (
            "PASS"
            if isinstance(rows, list) and len(rows) <= 100
            else "FAIL"
        ),
        "result_columns": "PASS",
        "aggregate_values": "PASS",
        "group_values": "PASS",
        "result_limit_reached": (
            "REVIEW"
            if isinstance(rows, list) and len(rows) == 100
            else "PASS"
        ),
    }

    if not isinstance(rows, list) or len(rows) > 100:
        checks["aggregate_row_shape"] = "FAIL"
        checks["result_columns"] = "FAIL"
        checks["aggregate_values"] = "FAIL"
        checks["group_values"] = "FAIL"
    else:
        if query_type in {"count_all", "average", "min_max"} and len(rows) != 1:
            checks["aggregate_row_shape"] = "FAIL"
        expected = {column.lower() for column in expected_columns}
        for row in rows:
            if not isinstance(row, dict):
                checks["result_columns"] = "FAIL"
                break
            normalized_row = {
                str(column).lower(): value
                for column, value in row.items()
            }
            if set(normalized_row) != expected:
                checks["result_columns"] = "FAIL"
                break

            for column, kind in numeric_columns.items():
                value = normalized_row.get(column.lower())
                if value is None and kind == "aggregate":
                    continue
                try:
                    number = Decimal(str(value))
                    valid_number = number.is_finite()
                    if kind == "count":
                        valid_number = (
                            valid_number
                            and number >= 0
                            and number == number.to_integral_value()
                        )
                except (InvalidOperation, TypeError, ValueError):
                    valid_number = False
                if not valid_number:
                    checks["aggregate_values"] = "FAIL"
                    break

            dimension = intent.get("dimension")
            if dimension:
                value = normalized_row.get(str(dimension).lower())
                if isinstance(value, (dict, list, tuple, set, bytes)):
                    checks["group_values"] = "FAIL"

            if query_type == "min_max":
                minimum = normalized_row.get(minimum_column.lower())
                maximum = normalized_row.get(maximum_column.lower())
                if minimum is not None and maximum is not None:
                    try:
                        if Decimal(str(minimum)) > Decimal(str(maximum)):
                            checks["aggregate_values"] = "FAIL"
                    except (InvalidOperation, TypeError, ValueError):
                        checks["aggregate_values"] = "FAIL"

    if "FAIL" in checks.values():
        status = "FAIL"
    elif "REVIEW" in checks.values():
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "validation_status": status,
        "checks": checks,
        "row_count": len(rows) if isinstance(rows, list) else 0,
        "preview_truncated": (
            isinstance(rows, list) and len(rows) == 100
        ),
    }


def validate_generated_sql(generation: dict) -> dict[str, Any]:
    """Validate the supported SQL template without executing it."""

    sql = generation.get("sql")

    if generation.get("status") != "GENERATED" or not sql:
        return {
            "status": "REVIEW",
            "checks": {},
            "execution_allowed": False,
        }

    if generation.get("query_type") in SCHEMA_ANALYTICAL_QUERY_TYPES:
        intent = parse_schema_explorer_question(
            generation.get("question", "")
        )
        if (
            not intent
            or intent["query_type"] != generation.get("query_type")
        ):
            return {
                "status": "FAIL",
                "checks": {"supported_question_pattern": False},
                "execution_allowed": False,
            }

        expected_sql = _schema_analytical_sql(intent)
        statements = sqlparse.parse(sql)
        checks = {
            "supported_question_pattern": True,
            "generation_table_alignment": (
                str(generation.get("table", "")).lower()
                == intent["table"].lower()
            ),
            "generation_column_alignment": (
                {
                    str(column).lower()
                    for column in generation.get("required_columns", [])
                }
                == {
                    str(column).lower()
                    for column in intent["required_columns"]
                }
            ),
            "single_select": (
                len(statements) == 1
                and statements[0].get_type() == "SELECT"
            ),
            "exact_bounded_template": (
                " ".join(sql.split()).casefold()
                == " ".join(expected_sql.split()).casefold()
            ),
            "no_sql_comments": not bool(
                re.search(r"--|/\*|\*/|#", sql)
            ),
            "gold_table_scope": intent["table"].lower().startswith("gold_"),
            "row_limit": bool(
                re.search(r"\bLIMIT\s+100\s*$", sql, re.IGNORECASE)
            ),
        }
        status = "PASS" if all(checks.values()) else "FAIL"
        return {
            "status": status,
            "checks": checks,
            "execution_allowed": status == "PASS",
            "note": (
                "Exact schema-bound analytical template; "
                "read-only execution is limited to 100 result rows."
            ),
        }

    statements = sqlparse.parse(sql)

    single_select = (
        len(statements) == 1
        and statements[0].get_type() == "SELECT"
    )

    expected_table = ".".join(
        quote_identifier(value)
        for value in (
            os.environ["DATABRICKS_CATALOG"],
            os.environ["DATABRICKS_SCHEMA"],
            "gold_loan_portfolio_summary",
        )
    )

    normalized_sql = " ".join(sql.split())

    checks = {
        "single_select": single_select,
        "expected_table": f"FROM {expected_table}" in normalized_sql,
        "required_columns": all(
            re.search(rf"\b{column}\b", normalized_sql, re.I)
            for column in generation["required_columns"]
        ),
        "required_filter": bool(
            re.search(
                r"\bWHERE\s+overdue_installments\s*>\s*0\b",
                normalized_sql,
                re.I,
            )
        ),
        "limit": bool(
            re.search(r"\bLIMIT\s+100\s*$", normalized_sql, re.I)
        ),
    }

    status = "PASS" if all(checks.values()) else "FAIL"

    return {
        "status": status,
        "checks": checks,
        "execution_allowed": False,
        "note": (
            "Template-level validation only. "
            "Independent SQL security and semantic checks "
            "are required before Databricks execution."
        ),
    }
