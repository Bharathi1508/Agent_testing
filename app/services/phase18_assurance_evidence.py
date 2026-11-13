from datetime import datetime, timezone
from uuid import uuid4

AGENT_ID = "sql_agent_real_001"
MODE = "langgraph_real_sql"


def build_assurance_evidence(report: dict) -> dict:

    if not isinstance(report, dict):
        raise ValueError("Report must be an object")

    if report.get("agent_id") != AGENT_ID:
        raise ValueError("Unexpected agent ID")

    if report.get("execution_mode") != MODE:
        raise ValueError("Unexpected execution mode")

    governance = report.get("governance")

    if not isinstance(governance, dict):
        raise ValueError("Missing governance information")

    if governance.get("production_approved") is not False:
        raise ValueError("Production approval must be false")

    if governance.get("database_execution_allowed") is not False:
        raise ValueError("Database execution must be disabled")

    results = report.get("results")

    if not isinstance(results, list) or not results:
        raise ValueError("Missing test results")

    if report.get("total_tests") != len(results):
        raise ValueError("Test count mismatch")

    passed = 0

    for result in results:

        if not isinstance(result, dict):
            raise ValueError("Invalid test result")

        if not isinstance(result.get("passed"), bool):
            raise ValueError("Missing test verdict")

        if result.get("execution_target") != "langgraph_local":
            raise ValueError("Unexpected execution target")

        response = result.get("response")

        if isinstance(response, dict):
            if response.get("database_executed") is True:
                raise ValueError("Database execution was reported")

        if result["passed"]:
            passed += 1

    failed = len(results) - passed

    if report.get("passed_tests") != passed:
        raise ValueError("Passed count mismatch")

    if report.get("failed_tests") != failed:
        raise ValueError("Failed count mismatch")

    return {
        "evidence_id": uuid4().hex,
        "source_run_id": report.get("run_id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "phase": "18.6",
        "agent_id": AGENT_ID,
        "execution_mode": MODE,
        "execution_target": "langgraph_local",
        "assurance_verdict": (
            "passed" if failed == 0 else "failed"
        ),
        "total_tests": len(results),
        "passed_tests": passed,
        "failed_tests": failed,
        "test_results": results,
        "governance": {
            "decision": "development_review_only",
            "production_approved": False,
            "database_execution_allowed": False,
        },
    }
