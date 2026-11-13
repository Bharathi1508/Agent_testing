
"""
HEAAP - Functional Assurance Service

Coordinates:
1. Dynamic functional testing
2. Report persistence
3. Assurance summary generation

This service does not approve or activate agents.
"""

from datetime import datetime, timezone
from typing import Any

from app.services.dynamic_test_runner import (
    run_dynamic_agent_tests,
)

from app.services.test_report_repository import (
    TestReportRepository,
)


class FunctionalAssuranceService:

    def __init__(self):
        self.repository = TestReportRepository()

    def run_assurance(
        self,
        agent_id: str,
    ) -> dict[str, Any]:

        # Step 1: Execute generated functional tests
        test_report = run_dynamic_agent_tests(
            agent_id
        )

        # Step 2: Persist complete test report
        saved_report = self.repository.save_report(
            test_report
        )

        # Step 3: Return assurance summary
        return {
            "agent_id": agent_id,
            "assurance_type": "functional",
            "status": saved_report["status"],
            "passed": saved_report["passed"],
            "report_id": saved_report["report_id"],
            "total_tests": saved_report["total_tests"],
            "passed_tests": saved_report["passed_tests"],
            "failed_tests": saved_report["failed_tests"],
            "error_tests": saved_report["error_tests"],
            "blocked_tests": saved_report["blocked_tests"],
            "unsupported_capabilities": saved_report[
                "unsupported_capabilities"
            ],
            "tested_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    def get_report(
        self,
        agent_id: str,
        report_id: str,
    ) -> dict[str, Any] | None:

        return self.repository.get_report(
            agent_id,
            report_id,
        )

    def list_reports(
        self,
        agent_id: str,
    ) -> list[dict[str, Any]]:

        return self.repository.list_reports(
            agent_id
        )


def run_functional_assurance(
    agent_id: str,
) -> dict[str, Any]:

    service = FunctionalAssuranceService()
    return service.run_assurance(agent_id)
