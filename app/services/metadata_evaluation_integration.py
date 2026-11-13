from typing import Any

from app.services.metadata_evaluation_engine import evaluate_metadata


def run_independent_evaluation(
    selection: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    """
    Add independent reference-based checks to the existing
    Supervisor response.

    This adapter does not fetch Databricks schema itself.
    It consumes the existing Supervisor's live-schema evidence.
    """

    expected_table = validation.get("expected_table")
    expected_columns = validation.get("expected_columns")

    checks = validation.get("checks") or {}

    if not expected_table or not expected_columns:
        return {
            "validation_status": "REVIEW",
            "reason": "Trusted reference expectation unavailable",
            "sql_execution_allowed": False,
        }

    if (
        checks.get("live_schema") != "PASS"
        or checks.get("table_exists") != "PASS"
        or checks.get("selected_columns_exist") != "PASS"
    ):
        return {
            "validation_status": "REVIEW",
            "reason": (
                "Verified live Databricks schema evidence "
                "is not available or did not pass"
            ),
            "sql_execution_allowed": False,
        }

    table = selection.get("primary_table")
    columns = selection.get("selected_columns") or []

    # This is a verified-selected-column snapshot,
    # not a complete independently fetched catalog.
    schema = {table: list(columns)} if table else {}

    expected = {
        "primary_table": expected_table,
        "required_columns": expected_columns,
    }

    result = evaluate_metadata(
        selection=selection,
        expected=expected,
        live_schema=schema,
    )

    result["evidence_source"] = (
        "Existing Supervisor validation response"
    )
    result["independent_schema_fetch"] = False
    result["sql_execution_allowed"] = False

    return result
