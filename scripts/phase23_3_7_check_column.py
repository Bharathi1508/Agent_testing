import json
import time
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

from app.registry.agent_registry import get_registered_agent
from app.governance.approval_service import is_approved
from app.services.dynamic_supervisor_service import execute_supervisor_request

AGENT_ID = "metadata_agent_001"
REPORT_DIR = Path("reports/phase23_3")

def main():
    manifest = get_registered_agent(AGENT_ID)

    if manifest is None:
        raise SystemExit("BLOCKED: Agent not registered")

    if manifest.status != "active" or not is_approved(manifest):
        raise SystemExit("BLOCKED: Agent not approved and active")

    if "check_column" not in manifest.capabilities:
        raise SystemExit("BLOCKED: check_column not declared")

    files = sorted(
        REPORT_DIR.glob("generated_tests_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not files:
        raise SystemExit("No generated tests found")

    document = json.loads(files[0].read_text(encoding="utf-8"))
    if document.get("agent_id") != AGENT_ID:
        raise SystemExit("BLOCKED: Test file belongs to another agent")

    tests = [
        t for t in document.get("tests", [])
        if t.get("capability") == "metadata_search"
    ]

    if not tests:
        raise SystemExit("No metadata_search tests found")

    results = []

    for test in tests:
        table = test["table"]
        column = test["column"]

        print("Testing:", table, column)

        started = time.perf_counter()

        try:
            response = execute_supervisor_request(
                capability="check_column",
                payload={
                    "action": "check_column",
                    "table_name": table,
                    "column_name": column,
                },
                preferred_agent_id=AGENT_ID,
            )

            if not isinstance(response, dict):
                raise ValueError("Invalid Supervisor response")

            if response.get("status") != "completed":
                raise ValueError("Supervisor execution not completed")

            if response.get("agent_id") != AGENT_ID:
                raise ValueError("Unexpected agent")

            if response.get("capability") != "check_column":
                raise ValueError("Unexpected capability")

            agent_response = response.get("result")

            if not isinstance(agent_response, dict):
                raise ValueError("Invalid agent response")

            if agent_response.get("status") != "success":
                raise ValueError("Agent execution unsuccessful")

            if agent_response.get("action") != "check_column":
                raise ValueError("Unexpected action")

            if agent_response.get("table_name") != table:
                raise ValueError("Unexpected table")

            if agent_response.get("column_name") != column:
                raise ValueError("Unexpected column")

            actual = agent_response.get("result")

            if not isinstance(actual, dict):
                raise ValueError("Invalid check_column result")

            exists = actual.get("exists")
            expected = test["expected_result"]["exists"]

            if type(exists) is not bool:
                raise ValueError("exists must be boolean")

            if exists:
                returned_column = actual.get("column")
                if not isinstance(returned_column, dict):
                    raise ValueError("Missing column details")
                if returned_column.get("column_name") != column:
                    raise ValueError("Returned column mismatch")

            status = "passed" if exists == expected else "failed"
            detail = f"Expected exists={expected}, actual={exists}"

        except Exception as exc:
            status = "error"
            detail = f"{type(exc).__name__}: {exc}"

        results.append({
            "test_id": test["test_id"],
            "table": table,
            "column": column,
            "status": status,
            "detail": detail,
            "duration_ms": round(
                (time.perf_counter() - started) * 1000, 2
            ),
        })

    counts = Counter(r["status"] for r in results)

    report = {
        "phase": "23.3.7",
        "agent_id": AGENT_ID,
        "capability": "check_column",
        "execution_path": "dynamic_supervisor",
        "verification_method": "generated_expected_boolean",
        "independent_databricks_verification": False,
        "total_tests": len(results),
        "passed": counts["passed"],
        "failed": counts["failed"],
        "errors": counts["error"],
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    path = REPORT_DIR / (
        "check_column_assurance_"
        + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        + ".json"
    )

    with path.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== PHASE 23.3.7 RESULTS ===")
    print("Total:", len(results))
    print("Passed:", counts["passed"])
    print("Failed:", counts["failed"])
    print("Errors:", counts["error"])
    print("Report:", path)

if __name__ == "__main__":
    main()
