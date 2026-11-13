
"""
HEAAP - Phase 14
Security Test Runner

Responsibilities:
1. Load dynamically generated security test cases.
2. Execute each case through the Dynamic Supervisor.
3. Validate expected security rejections.
4. Detect unexpected execution and errors.
5. Produce a structured security assurance report.

This runner does not hardcode agent IDs or test payloads.
"""

import logging
import time

from datetime import datetime, timezone
from typing import Any

from app.services.security_test_case_generator import (
    generate_security_test_cases,
)

from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
)


logger = logging.getLogger(__name__)


class SecurityTestRunner:
    """
    Runs security tests against registered HEAAP agents.
    """

    CAPABILITY_TESTS = {
        "SEC_001",
        "SEC_003",
    }

    UNKNOWN_AGENT_TESTS = {
        "SEC_002",
    }

    AUTHORIZATION_EXCEPTIONS = {
        "agentnotapprovederror",
        "agentnotfounderror",
        "supervisorauthorizationerror",
        "permissionerror",
        "capabilitynotallowederror",
    }

    @staticmethod
    def _expected_rejection(
        test_id: str,
        message: str,
        exception_type: str = "",
    ) -> bool:
        """
        Confirm that an expected authorization exception
        matches the security scenario.

        Generic ValueError and runtime exceptions are
        not treated as successful security rejections.
        """

        message = message.lower()
        exception_type = exception_type.lower()

        if exception_type not in (
            SecurityTestRunner.AUTHORIZATION_EXCEPTIONS
        ):
            return False

        if test_id in SecurityTestRunner.CAPABILITY_TESTS:
            return any(
                phrase in message
                for phrase in (
                    "not eligible for capability",
                    "does not support capability",
                    "not declared",
                    "not supported",
                    "not allowed",
                    "unsupported capability",
                )
            )

        if test_id in SecurityTestRunner.UNKNOWN_AGENT_TESTS:
            return any(
                phrase in message
                for phrase in (
                    "not registered",
                    "not found",
                    "unknown agent",
                    "agent does not exist",
                )
            )

        return False

    def run_test_case(
        self,
        test_case: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute one trusted, generated security test case.
        """

        start_time = time.perf_counter()

        test_id = test_case["test_id"]
        agent_id = test_case["agent_id"]
        capability = test_case["capability"]
        payload = test_case["input"]

        status = "error"
        passed = False
        observation = ""

        try:
            response = execute_supervisor_request(
                capability=capability,
                payload=payload,
                preferred_agent_id=agent_id,
            )

            # Any normal execution response means the
            # negative security test did not prove denial.
            if isinstance(response, dict):
                response_status = str(
                    response.get("status", "")
                ).lower()

                if response_status in {
                    "blocked",
                    "denied",
                    "rejected",
                    "forbidden",
                }:
                    status = "inconclusive"
                    observation = (
                        "Supervisor returned a rejection "
                        "status without a verified "
                        "security reason."
                    )
                else:
                    status = "failed"
                    observation = (
                        "Supervisor returned a response "
                        "instead of rejecting the "
                        "security test."
                    )

            else:
                status = "failed"
                observation = (
                    "Supervisor returned an unexpected "
                    "response instead of rejecting "
                    "the request."
                )

        except Exception as exc:

            exception_type = type(exc).__name__
            exception_message = str(exc)

            if self._expected_rejection(
                test_id=test_id,
                message=exception_message,
                exception_type=exception_type,
            ):
                status = "passed"
                passed = True

                observation = (
                    f"{exception_type}: "
                    f"{exception_message}"
                )

            else:
                status = "error"

                observation = (
                    "Unexpected execution error: "
                    f"{exception_type}: "
                    f"{exception_message}"
                )

                logger.warning(
                    "Security test %s encountered "
                    "an unexpected error: %s",
                    test_id,
                    exception_type,
                )

        execution_time_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        return {
            "test_id": test_id,
            "agent_id": agent_id,
            "capability": capability,
            "status": status,
            "passed": passed,
            "expected_outcome": test_case.get(
                "expected_outcome",
                "blocked",
            ),
            "observation": observation,
            "execution_time_ms": execution_time_ms,
            "tested_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    def run_agent_tests(
        self,
        agent_id: str,
    ) -> dict[str, Any]:
        """
        Generate and run all security tests for an agent.
        """

        generated = generate_security_test_cases(
            agent_id
        )

        test_cases = generated.get(
            "test_cases",
            []
        )

        if generated.get("status") != "generated":
            return {
                "agent_id": agent_id,
                "assurance_type": "security",
                "status": "error",
                "passed": False,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "error_tests": 1,
                "inconclusive_tests": 0,
                "results": [],
                "observation": (
                    "Security test generation failed: "
                    f"{generated.get('status')}"
                ),
            }

        results = []

        for test_case in test_cases:
            result = self.run_test_case(
                test_case
            )
            results.append(result)

        passed_tests = sum(
            result["status"] == "passed"
            for result in results
        )

        failed_tests = sum(
            result["status"] == "failed"
            for result in results
        )

        error_tests = sum(
            result["status"] == "error"
            for result in results
        )

        inconclusive_tests = sum(
            result["status"] == "inconclusive"
            for result in results
        )

        total_tests = len(results)

        overall_passed = (
            total_tests > 0
            and passed_tests == total_tests
        )

        return {
            "agent_id": agent_id,
            "assurance_type": "security",
            "status": (
                "passed"
                if overall_passed
                else "failed"
            ),
            "passed": overall_passed,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "inconclusive_tests": inconclusive_tests,
            "results": results,
        }


def run_security_agent_tests(
    agent_id: str,
) -> dict[str, Any]:
    """
    Public entry point for HEAAP security testing.
    """

    runner = SecurityTestRunner()

    return runner.run_agent_tests(agent_id)
