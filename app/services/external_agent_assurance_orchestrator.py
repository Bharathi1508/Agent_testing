"""HEAAP Phase 19.3 - External Agent Assurance Orchestrator."""

from datetime import datetime, timezone

from app.services.external_agent_router import ExternalAgentRouter
from app.services.external_agent_approval_gate import (
    validate_onboarding_approval,
)
from app.services.external_agent_contract_testing import (
    run_external_contract_tests,
)


class ExternalAgentAssuranceOrchestrator:

    def __init__(self, router=None):
        self.router = (
            router if router is not None
            else ExternalAgentRouter()
        )

    def register_reviewed_agent(self, manifest, review):
        return self.router.register_agent(manifest, review)

    def run_assurance(
        self,
        capability,
        tests,
        *,
        agent_id=None,
        approved_run=False,
    ):

        if approved_run is not True:
            raise PermissionError(
                "Explicit mock test-run approval required"
            )

        if not isinstance(tests, list) or not tests:
            raise ValueError("Nonempty test list required")

        route = self.router.route(
            capability,
            agent_id=agent_id,
        )

        selected_id = route["agent_id"]
        record = self.router.agents[selected_id]

        manifest = record["manifest"]
        review = record["review"]

        validate_onboarding_approval(review, manifest)

        for test in tests:
            if not isinstance(test, dict):
                raise ValueError("Each test must be an object")

            if test.get("capability") != capability:
                raise ValueError(
                    "Test capability does not match route"
                )

        if route["adapter_type"] != "databricks_mock":
            raise PermissionError("Unsupported adapter type")

        report = run_external_contract_tests(
            manifest,
            tests,
            approved_run=True,
        )

        total = report["total_tests"]
        passed = report["passed_tests"]
        failed = report["failed_tests"]

        verdict = (
            "passed"
            if failed == 0 and passed == total
            else "failed"
        )

        return {
            "phase": "19.3",
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "agent_id": selected_id,
            "capability": capability,
            "route": route,
            "execution_mode": "databricks_mock",
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": failed,
            "verdict": verdict,
            "results": report["results"],
            "governance": {
                "mock_run_authorized": True,
                "production_approved": False,
                "live_endpoint_invoked": False,
                "database_executed": False,
            },
        }
