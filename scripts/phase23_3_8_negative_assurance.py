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
from app.services.dynamic_supervisor_service import execute_supervisor_request

AGENT_ID = "metadata_agent_001"
TABLE = "gold_loan_portfolio_summary"
REPORT_DIR = Path("reports/phase23_3")

def normalize_type(value):
    aliases = {
        "INTEGER": "INT",
        "LONG": "BIGINT",
        "SHORT": "SMALLINT",
    }
    value = str(value).strip().upper()
    return aliases.get(value, value)

def invoke_agent(action, table, column=None):
    payload = {
        "action": action,
        "table_name": table,
    }

    if column is not None:
        payload["column_name"] = column

    response = execute_supervisor_request(
        capability=action,
        payload=payload,
        preferred_agent_id=AGENT_ID,
    )

    if not isinstance(response, dict):
        raise ValueError("Invalid Supervisor response")

    if response.get("status") != "completed":
        raise ValueError("Supervisor did not complete")

    if response.get("agent_id") != AGENT_ID:
        raise ValueError("Unexpected agent")

    if response.get("capability") != action:
        raise ValueError("Unexpected capability")

    agent = response.get("result")

    if not isinstance(agent, dict):
        raise ValueError("Invalid agent response")

    if agent.get("status") != "success":
        raise ValueError("Agent returned unsuccessful status")

    if agent.get("action") != action:
        raise ValueError("Unexpected action")

    if agent.get("table_name") != table:
        raise ValueError("Unexpected table")

    if column is not None and agent.get("column_name") != column:
        raise ValueError("Unexpected column")

    return agent.get("result")

def run_case(case_id, action, table, column, expected):
    started = time.perf_counter()

    try:
        result = invoke_agent(action, table, column)

        if action == "check_column":
            if not isinstance(result, dict):
                raise ValueError("Expected dictionary")

            exists = result.get("exists")

            if type(exists) is not bool:
                raise ValueError("Invalid exists value")

            if exists != expected["exists"]:
                status = "failed"
                detail = f"Expected {expected['exists']}, got {exists}"

            elif exists:
                metadata = result.get("column")

                if not isinstance(metadata, dict):
                    raise ValueError("Missing column metadata")

                actual_name = metadata.get("column_name")
                actual_type = normalize_type(metadata.get("data_type"))

                if (
                    actual_name != column
                    or actual_type != expected["data_type"]
                ):
                    status = "failed"
                    detail = (
                        f"Expected {column}:{expected['data_type']}, "
                        f"got {actual_name}:{actual_type}"
                    )
                else:
                    status = "passed"
                    detail = "Column existence and type verified"
            else:
                status = "passed"
                detail = "Nonexistent column correctly rejected"

        elif action == "get_columns":
            if not isinstance(result, list):
                raise ValueError("Expected column list")

            actual = {}

            for item in result:
                if not isinstance(item, dict):
                    raise ValueError("Invalid column item")

                name = item.get("column_name")
                dtype = item.get("data_type")

                if not isinstance(name, str) or not isinstance(dtype, str):
                    raise ValueError("Missing column metadata")

                key = name.lower()

                if key in actual:
                    raise ValueError("Duplicate column")

                actual[key] = normalize_type(dtype)

            status = "passed" if actual == expected else "failed"
            detail = (
                "Full schema matched"
                if status == "passed"
                else "Schema differs from Databricks"
            )

        else:
            raise ValueError("Unsupported test action")

    except Exception as exc:
        status = "error"
        detail = f"{type(exc).__name__}: {exc}"

    return {
        "case_id": case_id,
        "action": action,
        "table": table,
        "column": column,
        "status": status,
        "detail": detail,
        "duration_ms": round(
            (time.perf_counter() - started) * 1000, 2
        ),
    }

def main():
    manifest = get_registered_agent(AGENT_ID)

    if manifest is None:
        raise SystemExit("BLOCKED: Agent not registered")

    if manifest.status != "active" or not is_approved(manifest):
        raise SystemExit("BLOCKED: Agent not approved")

    declared = set(manifest.capabilities)

    if not {"check_column", "get_columns"}.issubset(declared):
        raise SystemExit("BLOCKED: Missing required capabilities")

    for identifier in (DATABRICKS_CATALOG, DATABRICKS_SCHEMA, TABLE):
        if not re.fullmatch(r"[A-Za-z0-9_]+", identifier):
            raise SystemExit("Invalid SQL identifier")

    sql = f"""
        SELECT column_name, data_type
        FROM `{DATABRICKS_CATALOG}`.information_schema.columns
        WHERE table_schema = '{DATABRICKS_SCHEMA}'
          AND table_name = '{TABLE}'
    """

    rows = execute_query(sql)

    if not rows:
        raise SystemExit("Trusted Databricks metadata unavailable")

    trusted = {
        row["column_name"].lower(): normalize_type(row["data_type"])
        for row in rows
    }

    cases = []

    for column, dtype in sorted(trusted.items()):
        cases.append((
            f"positive_{column}",
            "check_column",
            TABLE,
            column,
            {"exists": True, "data_type": dtype},
        ))

    for column in (
        "fake_loan_column_999",
        "nonexistent_field_999",
    ):
        if column in trusted:
            raise SystemExit("Negative test column exists in Databricks")

        cases.append((
            f"negative_{column}",
            "check_column",
            TABLE,
            column,
            {"exists": False},
        ))

    fake_table = "fake_loan_table_999"

    # The nonexistent-table behavior may be an error rather
    # than a successful exists=False response.
    cases.append((
        "negative_table",
        "check_column",
        fake_table,
        "loan_id",
        {"exists": False},
    ))

    cases.append((
        "full_schema",
        "get_columns",
        TABLE,
        None,
        trusted,
    ))

    results = []

    for case in cases:
        print("Testing:", case[0])
        results.append(run_case(*case))

    counts = Counter(r["status"] for r in results)

    report = {
        "phase": "23.3.8",
        "agent_id": AGENT_ID,
        "trusted_source": (
            f"databricks:{DATABRICKS_CATALOG}."
            f"{DATABRICKS_SCHEMA}.{TABLE}"
        ),
        "verification_method": "independent_databricks_schema",
        "total_tests": len(results),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "errors": counts["error"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    path = REPORT_DIR / (
        "metadata_negative_assurance_"
        + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        + ".json"
    )

    with path.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("\n=== PHASE 23.3.8 RESULTS ===")
    print("Total:", len(results))
    print("Passed:", counts["passed"])
    print("Failed:", counts["failed"])
    print("Errors:", counts["error"])
    print("Report:", path)

if __name__ == "__main__":
    main()
