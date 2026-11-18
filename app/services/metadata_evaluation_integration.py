import re
from typing import Any

from app.services.metadata_evaluation_engine import evaluate_metadata
from app.services.metadata_service import get_columns


_SCALAR_TYPE_PATTERN = (
    r"^(STRING|CHAR|VARCHAR|BOOLEAN|DATE|TIMESTAMP|"
    r"TINYINT|SMALLINT|INT|INTEGER|BIGINT|LONG|FLOAT|DOUBLE|"
    r"DECIMAL|NUMERIC)\b"
)
_NUMERIC_TYPE_PATTERN = (
    r"^(TINYINT|SMALLINT|INT|INTEGER|BIGINT|LONG|FLOAT|DOUBLE|"
    r"DECIMAL|NUMERIC)\b"
)


def run_independent_evaluation(
    selection: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    """
    Re-fetch live schema and compare it with a curated expectation or a
    strictly parsed schema-derived intent.
    """
    expected_table = validation.get("expected_table")
    expected_columns = validation.get("expected_columns")
    schema_bound = validation.get("reference_authority") == (
        "schema_bound_analytical_query_template"
    )

    if not expected_table or (
        not expected_columns and not schema_bound
    ):
        return {
            "validation_status": "REVIEW",
            "reason": "No approved glossary definition matches this question.",
            "evidence_source": "Business glossary",
            "independent_schema_fetch": False,
            "sql_execution_allowed": False,
        }

    try:
        rows = get_columns(expected_table)
        if not isinstance(rows, list) or not rows:
            raise ValueError("Independent live schema result is empty")

        live_column_types = {
            str(row["column_name"]).lower(): str(
                row.get("data_type") or ""
            ).upper()
            for row in rows
            if isinstance(row, dict) and row.get("column_name")
        }
        if not live_column_types:
            raise ValueError("Independent live schema has no column names")
    except Exception as exc:
        return {
            "validation_status": "ERROR",
            "reason": f"Independent Unity Catalog lookup failed: {exc}",
            "evidence_source": "Databricks Unity Catalog",
            "independent_schema_fetch": True,
            "sql_execution_allowed": False,
        }

    if schema_bound:
        intent = validation.get("schema_analytical_intent") or {}
        required_columns = {
            str(column).lower() for column in expected_columns or []
        }
        selected_columns = {
            str(column).lower()
            for column in selection.get("selected_columns", [])
        }
        checks = {
            "question_structure": "PASS",
            "table_correct": (
                "PASS"
                if str(selection.get("primary_table", "")).lower()
                == str(expected_table).lower()
                else "FAIL"
            ),
            "required_columns": (
                "PASS"
                if required_columns.issubset(selected_columns)
                else "FAIL"
            ),
            "column_minimality": (
                "PASS" if required_columns == selected_columns else "FAIL"
            ),
            "table_exists": "PASS",
            "selected_columns_exist": (
                "PASS"
                if selected_columns.issubset(live_column_types)
                else "FAIL"
            ),
            "business_glossary": "NOT_REQUIRED_SCHEMA_BOUND",
            "relationship_metadata": "NOT_REQUIRED",
            "filter_requirement": "NOT_REQUIRED",
        }

        dimension = intent.get("dimension")
        if dimension:
            checks["supported_dimension_type"] = (
                "PASS"
                if re.match(
                    _SCALAR_TYPE_PATTERN,
                    live_column_types.get(str(dimension).lower(), ""),
                )
                else "FAIL"
            )
        measure = intent.get("measure")
        if measure:
            checks["numeric_measure_type"] = (
                "PASS"
                if re.match(
                    _NUMERIC_TYPE_PATTERN,
                    live_column_types.get(str(measure).lower(), ""),
                )
                else "FAIL"
            )

        status = "FAIL" if "FAIL" in checks.values() else "PASS"
        result = {
            "validation_status": status,
            "checks": checks,
            "missing_columns": sorted(
                required_columns - set(live_column_types)
            ),
            "invalid_columns": [],
            "extra_columns": sorted(selected_columns - required_columns),
            "evidence_source": (
                "Strict schema-derived analytical intent + independently "
                "fetched Unity Catalog schema"
            ),
        }
    else:
        expected = {
            "primary_table": expected_table,
            "required_columns": expected_columns,
            "filter": validation.get("expected_filter"),
            "relationships": validation.get("expected_relationships", []),
            "join_required": validation.get("join_required", False),
        }
        result = evaluate_metadata(
            selection=selection,
            expected=expected,
            live_schema={expected_table: sorted(live_column_types)},
        )
        result["evidence_source"] = (
            "Curated code reference + independent Unity Catalog query"
        )
    result["reference_authority"] = validation.get(
        "reference_authority",
        "unknown",
    )
    result["independent_schema_fetch"] = True
    result["sql_execution_allowed"] = False
    return result
