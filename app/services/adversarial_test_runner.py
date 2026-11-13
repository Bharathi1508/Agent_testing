
"""
HEAAP - Phase 14, Step 5
Adversarial Test Runner

Initial controlled metadata-agent test runner.

Generates and evaluates negative-input tests.
Ambiguous failures are NOT considered passes.
"""

import time
from datetime import datetime, timezone

from app.registry.agent_registry import get_registered_agent
from app.governance.approval_service import is_approved

from app.services.adversarial_test_generator import (
    generate_adversarial_test_cases,
)

from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
)
from app.services.adversarial_response_adapter import (
    adapt_adversarial_success,
    adapt_adversarial_exception,
)

from app.services.adversarial_response_validator import (
    validate_adversarial_response,
)

class AdversarialTestRunner:

    ALLOWED_AGENT = "metadata_agent_001"

    SAFE_SCENARIOS = {
        ("list_tables", "unsupported_action"),
        ("list_tables", "invalid_action_type"),
        ("get_columns", "missing_table_name"),
        ("get_columns", "invalid_table_name_type"),
        ("check_column", "missing_column_name"),
        ("check_column", "invalid_column_name_type"),
        ("search_columns", "missing_search_term"),
        ("search_columns", "invalid_search_term_type"),
    }

    def run_agent_tests(self, agent_id: str):

        if agent_id != self.ALLOWED_AGENT:
            raise PermissionError(
                "Only the verified local Metadata Agent "
                "is supported in this initial runner."
            )

        manifest = get_registered_agent(agent_id)

        if manifest is None:
            raise ValueError(
                f"Agent '{agent_id}' is not registered"
            )

        if manifest.status != "active":
            raise PermissionError(
                "Agent must be active"
            )

        if not is_approved(manifest):
            raise PermissionError(
                "Agent must be approved"
            )

        if str(manifest.execution_type).lower() != "local":
            raise PermissionError(
                "Only local agents are supported"
            )

        generated = generate_adversarial_test_cases(
            agent_id
        )

        if generated.get("status") != "generated":
            raise ValueError(
                "No supported adversarial tests generated"
            )

        results = []

        for case in generated["test_cases"]:
            results.append(
                self.run_test_case(case, agent_id)
            )

        counts = {
            status: sum(
                result["status"] == status
                for result in results
            )
            for status in (
                "passed",
                "failed",
                "error",
                "inconclusive",
            )
        }

        total = len(results)
        passed = total > 0 and counts["passed"] == total

        return {
            "agent_id": agent_id,
            "assurance_type": "adversarial",
            "status": "passed" if passed else "incomplete",
            "passed": passed,
            "total_tests": total,
            "passed_tests": counts["passed"],
            "failed_tests": counts["failed"],
            "error_tests": counts["error"],
            "inconclusive_tests": counts["inconclusive"],
            "results": results,
        }

    def run_test_case(self, case, expected_agent_id):

        start = time.perf_counter()
        status = "inconclusive"
        observation = ""

        try:
            generated = generate_adversarial_test_cases(
                expected_agent_id
            )

            # Compare against trusted generator output,
            # rather than trusting caller-supplied payloads.
            trusted_cases = {
                item["test_id"]: item
                for item in generated.get("test_cases", [])
            }

            trusted = trusted_cases.get(
                case.get("test_id")
            )

            if trusted is None or case != trusted:
                raise ValueError(
                    "Test case differs from trusted template"
                )

            if case["agent_id"] != expected_agent_id:
                raise ValueError(
                    "Agent ID mismatch"
                )

            if case["execution_mode"] != "sandbox_only":
                raise ValueError(
                    "Sandbox-only test required"
                )

            if case["risk"] != "low":
                raise ValueError(
                    "Only low-risk scenarios are supported"
                )

            scenario = (
                case["capability"],
                case["scenario"],
            )

            if scenario not in self.SAFE_SCENARIOS:
                raise ValueError(
                    "Scenario is not allowlisted"
                )

        except (ValueError, KeyError, TypeError) as exc:
            status = "error"
            observation = (
                f"Test configuration error: {exc}"
            )

        else:
            try:
                response = execute_supervisor_request(
                    capability=case["capability"],
                    payload=case["input"].copy(),
                    preferred_agent_id=expected_agent_id,
                )

                adapted_response = adapt_adversarial_success(
                    response
                )

            except Exception as exc:
                adapted_response = adapt_adversarial_exception(
                    exc
                )

            validation = validate_adversarial_response(
                case,
                adapted_response,
            )

            status = validation["status"]
            observation = validation["reason"]

            if adapted_response.get("exception_chain"):
                observation += (
                    " | Exception chain: "
                    + repr(adapted_response["exception_chain"])
                )

        elapsed = round(
            (time.perf_counter() - start) * 1000,
            2
        )

        return {
            "test_id": case.get("test_id"),
            "agent_id": expected_agent_id,
            "capability": case.get("capability"),
            "scenario": case.get("scenario"),
            "status": status,
            "passed": status == "passed",
            "expected_outcome": case.get(
                "expected_outcome"
            ),
            "observation": observation,
            "execution_time_ms": elapsed,
            "tested_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }


def run_adversarial_agent_tests(agent_id: str):
    return AdversarialTestRunner().run_agent_tests(
        agent_id
    )
