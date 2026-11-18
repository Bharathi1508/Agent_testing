from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from app.services.supervisor_metadata_selector import select_metadata
from app.services.live_metadata_validator import validate_with_live_schema
from app.services.metadata_evaluation_integration import run_independent_evaluation
from app.services.heaap_sql_assurance import (
    SCHEMA_ANALYTICAL_QUERY_TYPES,
    generate_sql,
    parse_schema_explorer_question,
    validate_generated_sql,
    validate_query_results,
)
from app.services.independent_sql_supervisor import supervise_sql
from app.adapters.databricks_client import execute_query


REPORT_DIR = Path("reports/pipeline")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def _schema_explorer_selection(
    question: str,
) -> dict[str, Any] | None:
    intent = parse_schema_explorer_question(question)
    if not intent:
        return None
    return {
        "question": question,
        "primary_table": intent["table"],
        "selected_columns": intent["required_columns"],
        "selection_status": "SCHEMA_DERIVED",
        "selection_source": "schema_bound_analytical_query",
        "reference_rule_id": None,
        "expected_filter": None,
        "relationships": [],
        "join_required": False,
        "sql_execution_allowed": False,
    }


def _apply_schema_explorer_reference(
    question: str,
    selection: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    intent = parse_schema_explorer_question(question)
    if not intent:
        return validation

    validation["expected_table"] = intent["table"]
    validation["expected_columns"] = intent["required_columns"]
    validation["expected_filter"] = None
    validation["expected_relationships"] = []
    validation["join_required"] = False
    validation["reference_authority"] = (
        "schema_bound_analytical_query_template"
    )
    validation["schema_analytical_intent"] = intent

    checks = validation.setdefault("checks", {})
    checks["question_structure"] = "PASS"
    checks["reference_definition"] = "NOT_REQUIRED_SCHEMA_BOUND"
    checks["business_glossary"] = "NOT_REQUIRED_SCHEMA_BOUND"
    checks["table_correct"] = (
        "PASS"
        if selection["primary_table"].lower() == intent["table"].lower()
        else "FAIL"
    )
    required_columns = {
        str(column).lower() for column in intent["required_columns"]
    }
    selected_columns = {
        str(column).lower()
        for column in selection.get("selected_columns", [])
    }
    checks["required_columns"] = (
        "PASS"
        if required_columns.issubset(selected_columns)
        else "FAIL"
    )
    checks["column_minimality"] = (
        "PASS" if required_columns == selected_columns else "FAIL"
    )
    checks["relationship_metadata"] = "NOT_REQUIRED"
    checks["filter_requirement"] = "NOT_REQUIRED"
    checks["filter_application"] = "NOT_REQUIRED"

    live_checks = (
        "table_exists",
        "selected_columns_exist",
        "live_schema",
        "live_schema_query",
    )
    if any(checks.get(name) == "ERROR" for name in live_checks):
        validation["validation_status"] = "ERROR"
    elif any(checks.get(name) == "FAIL" for name in live_checks):
        validation["validation_status"] = "FAIL"
    elif all(checks.get(name) == "PASS" for name in live_checks):
        validation["validation_status"] = "PASS"
        validation.setdefault("evidence", []).append(
            "The explicit schema-derived analytical question template and all "
            "referenced Gold-table metadata passed live Unity Catalog checks."
        )
    else:
        validation["validation_status"] = "REVIEW"

    return validation


def run_pipeline(question: str) -> dict[str, Any]:
    selection = _schema_explorer_selection(question)
    if selection is None:
        selection = select_metadata(question)

    validation = validate_with_live_schema(
        question, selection
    )
    validation = _apply_schema_explorer_reference(
        question, selection, validation
    )

    independent = run_independent_evaluation(
        selection, validation
    )

    statuses = [
        validation.get("validation_status"),
        independent.get("validation_status"),
    ]

    if "FAIL" in statuses:
        metadata_status = "FAIL"
    elif "ERROR" in statuses:
        metadata_status = "ERROR"
    elif all(status == "PASS" for status in statuses):
        metadata_status = "PASS"
    else:
        metadata_status = "REVIEW"

    generation = {
        "status": "NOT_STARTED",
        "sql": None,
    }

    sql_assurance = {
        "status": "NOT_TESTED",
        "execution_allowed": False,
    }

    sql_supervisor = {
        "status": "NOT_TESTED",
        "execution_allowed": False,
    }
    execution = {
        "status": "NOT_EXECUTED",
        "row_count": 0,
        "rows": [],
        "result_validation": {
            "validation_status": "NOT_TESTED",
            "checks": {},
            "row_count": 0,
            "preview_truncated": False,
        },
    }

    if metadata_status == "PASS":
        generation = generate_sql(question, selection)
        sql_assurance = validate_generated_sql(generation)

        if (
            generation.get("status") == "GENERATED"
            and sql_assurance.get("status") == "PASS"
        ):
            sql_supervisor = supervise_sql(
                question,
                generation["sql"],
                selection,
            )

    execution_allowed = (
        metadata_status == "PASS"
        and generation.get("query_type")
        in SCHEMA_ANALYTICAL_QUERY_TYPES
        and generation.get("status") == "GENERATED"
        and sql_assurance.get("status") == "PASS"
        and sql_supervisor.get("status") == "PASS"
        and sql_supervisor.get("execution_allowed") is True
    )
    if execution_allowed:
        try:
            rows = execute_query(generation["sql"])
            intent = parse_schema_explorer_question(question)
            result_validation = validate_query_results(
                generation["query_type"],
                intent or {},
                rows,
            )
            execution = {
                "status": "SUCCEEDED",
                "row_count": len(rows),
                "rows": rows,
                "result_validation": result_validation,
            }
        except Exception as exc:
            execution = {
                "status": "ERROR",
                "row_count": 0,
                "rows": [],
                "result_validation": {
                    "validation_status": "NOT_TESTED",
                    "checks": {},
                    "row_count": 0,
                    "preview_truncated": False,
                },
                "error": f"{type(exc).__name__}: {exc}",
            }

    if metadata_status != "PASS":
        orchestrator_status = metadata_status
    elif generation.get("status") != "GENERATED":
        orchestrator_status = generation.get("status", "ERROR")
    elif sql_assurance.get("status") != "PASS":
        orchestrator_status = sql_assurance.get("status", "ERROR")
    elif sql_supervisor.get("status") != "PASS":
        orchestrator_status = sql_supervisor.get("status", "ERROR")
    elif execution["status"] == "ERROR":
        orchestrator_status = "ERROR"
    elif (
        execution["status"] == "SUCCEEDED"
        and execution["result_validation"]["validation_status"] == "PASS"
    ):
        orchestrator_status = "PASS"
    else:
        orchestrator_status = "BLOCKED"

    agent_runs = [
        {
            "agent_id": "banking_assurance_orchestrator",
            "name": "Banking Assurance Orchestrator",
            "role": "Coordinate specialist agents and enforce stage gates.",
            "status": orchestrator_status,
            "summary": (
                "Coordinated metadata, semantics, SQL, and result checks."
            ),
        },
        {
            "agent_id": "banking_question_agent",
            "name": "Banking Question Agent",
            "role": "Map the business question to a candidate Gold table and columns.",
            "status": (
                "PASS"
                if selection.get("primary_table")
                and selection.get("selected_columns")
                else "REVIEW"
            ),
            "summary": (
                f"Selected {selection['primary_table']}."
                if selection.get("primary_table")
                else "No Gold table was selected."
            ),
        },
        {
            "agent_id": "gold_metadata_assurance_agent",
            "name": "Gold Metadata Assurance Agent",
            "role": "Validate selected tables and columns against live metadata.",
            "status": validation.get("validation_status", "ERROR"),
            "summary": "Live metadata and expected-column checks.",
        },
        {
            "agent_id": "banking_semantics_agent",
            "name": "Banking Semantics Agent",
            "role": "Independently review business meaning and schema alignment.",
            "status": independent.get("validation_status", "ERROR"),
            "summary": independent.get(
                "reason",
                "Independent semantic and schema checks.",
            ),
        },
        {
            "agent_id": "banking_sql_generation_agent",
            "name": "Banking SQL Generation Agent",
            "role": "Generate a bounded read-only query after metadata passes.",
            "status": (
                generation.get("status", "ERROR")
                if metadata_status == "PASS"
                else "BLOCKED"
            ),
            "summary": generation.get(
                "reason",
                "Generated SQL from a supported banking query template."
                if generation.get("status") == "GENERATED"
                else "Waiting for metadata assurance to pass.",
            ),
        },
        {
            "agent_id": "banking_sql_assurance_agent",
            "name": "SQL Assurance Agent",
            "role": "Check generated SQL against the approved safe template.",
            "status": (
                sql_assurance.get("status", "ERROR")
                if metadata_status == "PASS"
                else "BLOCKED"
            ),
            "summary": sql_assurance.get(
                "note",
                "SQL template checks run only after metadata passes.",
            ),
        },
        {
            "agent_id": "independent_sql_supervisor",
            "name": "Independent SQL Supervisor",
            "role": "Independently gate SQL execution.",
            "status": (
                sql_supervisor.get("status", "ERROR")
                if sql_supervisor.get("status") != "NOT_TESTED"
                else "BLOCKED"
            ),
            "summary": (
                "Execution is allowed only after independent SQL checks pass."
            ),
        },
        {
            "agent_id": "banking_result_validation_agent",
            "name": "Banking Result Validation Agent",
            "role": "Validate query result shape, values, and row limits.",
            "status": (
                "ERROR"
                if execution["status"] == "ERROR"
                else execution["result_validation"]["validation_status"]
                if execution["status"] == "SUCCEEDED"
                else "BLOCKED"
            ),
            "summary": (
                "Validated query output."
                if execution["status"] == "SUCCEEDED"
                else "Waiting for approved SQL execution."
            ),
        },
    ]

    report = {
        "question": question,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_runs": agent_runs,
        "selection": selection,
        "metadata_validation": validation,
        "independent_evaluation": independent,
        "metadata_assurance_status": metadata_status,
        "metadata_decision": (
            "CORRECTION_RETEST"
            if metadata_status in ("FAIL", "ERROR")
            else "HUMAN_REVIEW"
            if metadata_status == "REVIEW"
            else "PROCEED_TO_SQL_GENERATION"
        ),
        "sql_generation": generation,
        "sql_generation_status": generation["status"],
        "sql_assurance": sql_assurance,
        "sql_assurance_status": sql_assurance["status"],
        "sql_supervisor": sql_supervisor,
        "sql_supervisor_status": sql_supervisor["status"],
        "sql_execution_status": execution["status"],
        "sql_execution_allowed": execution_allowed,
        "sql_execution": execution,
        "result_validation_status": execution["result_validation"][
            "validation_status"
        ],
    }

    filename = (
        datetime.now(timezone.utc)
        .strftime("%Y%m%d_%H%M%S_%f")
        + ".json"
    )

    path = REPORT_DIR / filename

    path.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )

    report["report_path"] = str(path)

    return report
