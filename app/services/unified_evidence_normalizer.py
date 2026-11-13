"""HEAAP Phase 18.7: Unified assurance evidence normalization."""

from datetime import datetime, timezone
from uuid import uuid4


def _require_count(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"Invalid {name}")
    return value


def normalize_assurance_report(report):
    if not isinstance(report, dict):
        raise ValueError("Report must be an object")

    agent_id = report.get("agent_id")
    run_id = report.get("run_id")
    execution_mode = report.get("execution_mode")

    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("Missing agent ID")

    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("Missing run ID")

    if not isinstance(execution_mode, str) or not execution_mode.strip():
        raise ValueError("Missing execution mode")

    governance = report.get("governance")

    if not isinstance(governance, dict):
        raise ValueError("Missing governance")

    if governance.get("production_approved") is not False:
        raise ValueError("Production approval must be false")

    if governance.get("database_execution_allowed") is not False:
        raise ValueError("Database execution must be disabled")

    results = report.get("results")

    if not isinstance(results, list) or not results:
        raise ValueError("Missing test results")

    total = _require_count(report.get("total_tests"), "total_tests")
    passed = _require_count(report.get("passed_tests"), "passed_tests")
    failed = _require_count(report.get("failed_tests"), "failed_tests")

    if total != len(results) or passed + failed != total:
        raise ValueError("Inconsistent test counts")

    normalized_results = []
    actual_passed = 0

    for index, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            raise ValueError("Invalid test result")

        test_id = result.get("test_id")

        if not isinstance(test_id, str) or not test_id.strip():
            raise ValueError(f"Missing test ID at position {index}")

        outcome = result.get("passed")

        if type(outcome) is not bool:
            raise ValueError(f"Missing boolean verdict for {test_id}")

        if outcome:
            actual_passed += 1

        response = result.get("response")

        if isinstance(response, dict):
            if response.get("database_executed") is True:
                raise ValueError("Unexpected database execution reported")

        normalized_results.append({
            "test_id": test_id,
            "capability": result.get("capability"),
            "expected_status": result.get("expected_status"),
            "actual_status": result.get("actual_status"),
            "expected_error_code": result.get("expected_error_code"),
            "actual_error_code": result.get("actual_error_code"),
            "passed": outcome,
            "execution_target": result.get("execution_target"),
            "response": response,
        })

    if actual_passed != passed:
        raise ValueError("Passed count does not match results")

    verdict = "passed" if failed == 0 else "failed"

    return {
        "evidence_id": uuid4().hex,
        "source_run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "phase": "18.7",
        "agent_id": agent_id,
        "execution_mode": execution_mode,
        "execution_target": report.get("execution_target"),
        "assurance_verdict": verdict,
        "total_tests": total,
        "passed_tests": passed,
        "failed_tests": failed,
        "test_results": normalized_results,
        "governance": {
            "decision": "development_review_only",
            "production_approved": False,
            "database_execution_allowed": False,
        },
    }
