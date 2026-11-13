from __future__ import annotations

from typing import Any

from app.services.metadata_service import list_tables, get_columns
from app.services.metadata_validation_engine import validate_metadata


def validate_with_live_schema(
    question: str,
    selection: dict[str, Any],
) -> dict[str, Any]:
    """
    Independently check proposed metadata against the current
    Databricks catalog, then apply curated business reference rules.
    """
    result = validate_metadata(question, selection)

    table_name = selection.get("primary_table")
    selected_columns = {
        str(c).lower()
        for c in selection.get("selected_columns", [])
    }

    checks = result.setdefault("checks", {})
    evidence = result.setdefault("evidence", [])

    checks["table_exists"] = "NOT_VERIFIED"
    checks["selected_columns_exist"] = "NOT_VERIFIED"
    checks["live_schema"] = "NOT_VERIFIED"

    if not isinstance(table_name, str) or not table_name.strip():
        checks["table_exists"] = "FAIL"
        evidence.append("No primary table was selected.")
    else:
        try:
            tables = list_tables()

            if not isinstance(tables, list):
                raise ValueError("Unexpected table-list response")

            available_tables = {
                str(row["table_name"]).lower()
                for row in tables
                if isinstance(row, dict) and row.get("table_name")
            }

            if not available_tables:
                raise ValueError("Table listing is empty")

            if table_name.lower() not in available_tables:
                checks["table_exists"] = "FAIL"
                evidence.append(
                    f"Selected table not found in catalog: {table_name}"
                )
            else:
                checks["table_exists"] = "PASS"

                columns = get_columns(table_name)

                if not isinstance(columns, list) or not columns:
                    raise ValueError("Column listing is empty or invalid")

                available_columns = {
                    str(row["column_name"]).lower()
                    for row in columns
                    if isinstance(row, dict) and row.get("column_name")
                }

                if not available_columns:
                    raise ValueError("No valid column names returned")

                missing_selected = sorted(
                    selected_columns - available_columns
                )

                expected_columns = {
                    str(c).lower()
                    for c in result.get("expected_columns", [])
                }
                missing_expected = sorted(
                    expected_columns - available_columns
                )

                checks["selected_columns_exist"] = (
                    "FAIL" if missing_selected else "PASS"
                )
                checks["live_schema"] = (
                    "FAIL" if missing_expected else "PASS"
                ) if expected_columns else "NOT_VERIFIED"

                evidence.append(
                    f"Live catalog contains {len(available_columns)} "
                    f"columns in {table_name}."
                )
                evidence.append(
                    f"Selected columns absent from catalog: "
                    f"{missing_selected}"
                )
                if expected_columns:
                    evidence.append(
                        f"Reference columns absent from catalog: "
                        f"{missing_expected}"
                    )

        except Exception as exc:
            evidence.append(
                "Live Databricks schema verification unavailable: "
                f"{type(exc).__name__}: {exc}"
            )

    if any(value == "FAIL" for value in checks.values()):
        result["validation_status"] = "FAIL"
    else:
        # Semantic completeness, SQL filters and query results
        # are not fully validated by schema checks.
        result["validation_status"] = "REVIEW"

    result["sql_execution_allowed"] = False

    return result
