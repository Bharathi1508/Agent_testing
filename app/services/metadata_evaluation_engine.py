from typing import Any


def evaluate_metadata(
    selection: dict[str, Any],
    expected: dict[str, Any],
    live_schema: dict[str, list[str]],
) -> dict[str, Any]:
    """
    Evaluate a metadata selection against trusted reference
    expectations and a verified schema snapshot.

    This function does not connect to Databricks itself.
    The caller must supply a trusted schema snapshot.
    """

    table = selection.get("primary_table")
    selected = set(selection.get("selected_columns") or [])

    expected_table = expected.get("primary_table")
    required = set(expected.get("required_columns") or [])
    required_relationships = expected.get("relationships") or []
    expected_filter = expected.get("filter")

    # Do not claim correctness without a trusted reference.
    if not expected_table or not required:
        return {
            "validation_status": "REVIEW",
            "reason": "Trusted reference expectation unavailable",
            "checks": {},
            "sql_execution_allowed": False,
        }

    # Missing schema evidence is a technical validation error.
    if live_schema is None:
        return {
            "validation_status": "ERROR",
            "reason": "Verified schema snapshot unavailable",
            "checks": {},
            "sql_execution_allowed": False,
        }

    table_correct = table == expected_table

    missing = sorted(required - selected)
    extra = sorted(selected - required)

    table_exists = table in live_schema

    actual_columns = set(live_schema.get(table, []))
    invalid_columns = sorted(selected - actual_columns)
    if expected_filter:
        normalize_filter = lambda value: "".join(
            str(value or "").lower().split()
        )
        filter_status = (
            "PASS"
            if normalize_filter(selection.get("expected_filter"))
            == normalize_filter(expected_filter)
            else "FAIL"
        )
    else:
        filter_status = "NOT_REQUIRED"

    if expected.get("join_required"):
        relationship_status = (
            "PASS"
            if required_relationships
            and selection.get("relationships") == required_relationships
            else "REVIEW"
        )
    else:
        relationship_status = "NOT_REQUIRED"

    checks = {
        "business_glossary": "PASS",
        "table_correct": (
            "PASS" if table_correct else "FAIL"
        ),
        "required_columns": (
            "PASS" if not missing else "FAIL"
        ),
        "table_exists": (
            "PASS" if table_exists else "FAIL"
        ),
        "selected_columns_exist": (
            "PASS"
            if table_exists and not invalid_columns
            else "FAIL"
        ),
        "column_minimality": (
            "PASS" if not extra else "REVIEW"
        ),
        "relationship_metadata": relationship_status,
        "filter_requirement": filter_status,
        "result_validation": "NOT_TESTED",
    }

    mandatory = [
        "table_correct",
        "required_columns",
        "table_exists",
        "selected_columns_exist",
    ]

    if any(checks[key] == "FAIL" for key in mandatory):
        status = "FAIL"
    elif (
        checks["column_minimality"] == "REVIEW"
        or checks["relationship_metadata"] == "REVIEW"
    ):
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "validation_status": status,
        "primary_table": table,
        "expected_table": expected_table,
        "selected_columns": sorted(selected),
        "required_columns": sorted(required),
        "expected_filter": expected_filter,
        "expected_relationships": required_relationships,
        "missing_columns": missing,
        "extra_columns": extra,
        "invalid_columns": invalid_columns,
        "checks": checks,
        "sql_execution_allowed": False,
    }
