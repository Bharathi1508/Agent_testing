"""Phase 19.0 - External agent contract tests."""

from app.adapters.external_agent_adapter import (
    ExternalAgentAdapter,
    ExternalAgentRequest,
    MockDatabricksTransport,
)


def run_external_contract_tests(manifest, tests, *, approved_run=False):
    if approved_run is not True:
        raise PermissionError("Explicit test-run approval required")

    if not isinstance(tests, list) or not tests:
        raise ValueError("Tests must be a nonempty list")

    adapter = ExternalAgentAdapter(
        manifest=manifest,
        transport=MockDatabricksTransport(),
    )

    results = []

    for test in tests:
        request = ExternalAgentRequest(
            agent_id=manifest["agent_id"],
            capability=test["capability"],
            payload=test["payload"],
        )

        response = adapter.execute(
            request,
            approved_run=True,
        )

        actual_error_code = response.response.get("error_code")

        passed = (
            response.status == test["expected_status"]
            and actual_error_code == test.get("expected_error_code")
        )

        results.append({
            "test_id": test["test_id"],
            "capability": test["capability"],
            "expected_status": test["expected_status"],
            "actual_status": response.status,
            "expected_error_code": test.get("expected_error_code"),
            "actual_error_code": actual_error_code,
            "passed": passed,
            "execution_target": response.execution_target,
            "response": response.response,
        })

    passed_tests = sum(r["passed"] for r in results)

    return {
        "agent_id": manifest["agent_id"],
        "execution_mode": "databricks_mock",
        "total_tests": len(results),
        "passed_tests": passed_tests,
        "failed_tests": len(results) - passed_tests,
        "results": results,
        "governance": {
            "production_approved": False,
            "database_execution_allowed": False,
            "live_endpoint_invocation_allowed": False,
        },
    }
