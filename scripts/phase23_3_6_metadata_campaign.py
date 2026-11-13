import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATABRICKS_CATALOG, DATABRICKS_SCHEMA
from app.adapters.databricks_client import execute_query
from app.registry.agent_registry import get_registered_agent
from app.governance.approval_service import is_approved
from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
)

AGENT_ID = "metadata_agent_001"
TABLE = "gold_loan_portfolio_summary"
REPORT_DIR = Path("reports/phase23_3")

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def normalize_type(value):
    aliases = {
        "LONG": "BIGINT",
        "INTEGER": "INT",
        "SHORT": "SMALLINT",
    }
    value = str(value).strip().upper()
    return aliases.get(value, value)

def extract_columns(response):
    if not isinstance(response, dict):
        raise ValueError("Agent response must be a dictionary")

    if response.get("status") != "success":
        raise ValueError("Agent response status is not success")

    result = response.get("result")

    if isinstance(result, dict):
        if isinstance(result.get("columns"), list):
            result = result["columns"]
        elif isinstance(result.get("result"), list):
            result = result["result"]

    if not isinstance(result, list):
        raise ValueError("Expected a list of column dictionaries")

    columns = {}

    for item in result:
        if not isinstance(item, dict):
            raise ValueError("Invalid column item")

        name = item.get("column_name")
        dtype = item.get("data_type")

        if not isinstance(name, str) or not isinstance(dtype, str):
            raise ValueError("Missing column_name or data_type")

        key = name.lower()

        if key in columns:
            raise ValueError("Duplicate column returned")

        columns[key] = normalize_type(dtype)

    return columns

def main():
    manifest = get_registered_agent(AGENT_ID)

    if manifest is None:
        raise SystemExit("BLOCKED: Agent not registered")

    if manifest.status != "active" or not is_approved(manifest):
        raise SystemExit("BLOCKED: Agent not active and approved")

    required = {"get_columns", "check_column"}
    declared = {
        str(capability).strip().lower()
        for capability in manifest.capabilities
    }

    if not required.issubset(declared):
        raise SystemExit("BLOCKED: Required capabilities not declared")

    files = sorted(
        REPORT_DIR.glob("generated_tests_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not files:
        raise SystemExit("No generated test file found")

    source_file = files[0]
    document = json.loads(source_file.read_text(encoding="utf-8"))
    tests = document.get("tests", [])

    if document.get("agent_id") != AGENT_ID:
        raise SystemExit("Generated test agent mismatch")

    if not tests:
        raise SystemExit("No tests to execute")

    for identifier in (DATABRICKS_CATALOG, DATABRICKS_SCHEMA, TABLE):
        if not re.fullmatch(r"[A-Za-z0-9_]+", identifier):
            raise SystemExit("Invalid SQL identifier")

    sql = f"""
    SELECT column_name, data_type
    FROM `{DATABRICKS_CATALOG}`.information_schema.columns
    WHERE table_schema = '{DATABRICKS_SCHEMA}'
      AND table_name = '{TABLE}'
    """

    trusted_rows = execute_query(sql)

    if not trusted_rows:
        raise SystemExit("Trusted Databricks schema unavailable")

    trusted = {
        row["column_name"].lower(): normalize_type(row["data_type"])
        for row in trusted_rows
    }

    expected_source = (
        f"databricks:{DATABRICKS_CATALOG}."
        f"{DATABRICKS_SCHEMA}.{TABLE}"
    )

    for test in tests:
        if (
            test.get("agent_id") != AGENT_ID
            or test.get("table") != TABLE
            or test.get("source") != expected_source
            or test.get("capability") not in {
                "metadata_search", "schema_discovery"
            }
        ):
            raise SystemExit("Generated test scope mismatch")

    started = time.perf_counter()

    response = execute_supervisor_request(
        capability="get_columns",
        payload={
            "action": "get_columns",
            "table_name": TABLE,
        },
        preferred_agent_id=AGENT_ID,
    )

    if not isinstance(response, dict):
        raise SystemExit("Invalid Supervisor response")

    if response.get("status") != "completed":
        raise SystemExit(
            "Supervisor execution unsuccessful: "
            + str(response.get("status"))
        )

    if response.get("agent_id") != AGENT_ID:
        raise SystemExit("Supervisor selected unexpected agent")

    agent_columns = extract_columns(response.get("result"))

    results = []

    for test in tests:
        column = test.get("column", "").lower()
        capability = test["capability"]

        expected_type = trusted.get(column)
        actual_type = agent_columns.get(column)

        if expected_type is None:
            status = "inconclusive"
            detail = "Column absent from fresh trusted snapshot"

        elif capability == "metadata_search":
            expected = test.get("expected_result", {}).get("exists")
            actual = column in agent_columns

            status = "passed" if actual == expected else "failed"
            detail = f"Expected exists={expected}, actual={actual}"

        else:
            generated_type = test.get(
                "expected_result", {}
            ).get("data_type")

            if normalize_type(generated_type) != expected_type:
                status = "inconclusive"
                detail = "Generated expected type differs from fresh schema"
            else:
                status = (
                    "passed"
                    if actual_type == expected_type
                    else "failed"
                )
                detail = (
                    f"Expected type={expected_type}, "
                    f"actual type={actual_type}"
                )

        results.append({
            "test_id": test["test_id"],
            "column": column,
            "capability": capability,
            "status": status,
            "detail": detail,
        })

    counts = Counter(item["status"] for item in results)

    overall = (
        "passed"
        if counts["passed"] == len(results)
        else "failed"
        if counts["failed"]
        else "incomplete"
    )

    report = {
        "platform": "HEAAP",
        "phase": "23.3.6",
        "agent_id": AGENT_ID,
        "table": TABLE,
        "source_file": str(source_file),
        "verification_source": expected_source,
        "execution_path": "dynamic_supervisor",
        "verification_scope": "get_columns_schema_comparison",
        "check_column_directly_tested": False,
        "generated_tests": len(tests),
        "passed_tests": counts["passed"],
        "failed_tests": counts["failed"],
        "inconclusive_tests": counts["inconclusive"],
        "status": overall,
        "execution_time_ms": round(
            (time.perf_counter() - started) * 1000, 2
        ),
        "tested_at": utc_now(),
        "results": results,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    filename = (
        "metadata_execution_"
        + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        + ".json"
    )

    report_path = REPORT_DIR / filename

    with report_path.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print(json.dumps({
        "status": overall,
        "generated_tests": len(tests),
        "passed_tests": counts["passed"],
        "failed_tests": counts["failed"],
        "inconclusive_tests": counts["inconclusive"],
        "execution_path": "dynamic_supervisor",
        "report": str(report_path),
    }, indent=2))

if __name__ == "__main__":
    main()
