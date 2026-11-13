"""
HEAAP - Phase 15.4
Controlled Dynamic Adversarial Test Runner

Current scope:
- Registered Metadata Agent only
- Trusted schema-generated negative tests
- No REST or Databricks execution
- No modification of Phase 14 files
"""

import json
import time
from collections import Counter
from datetime import datetime, timezone

from app.registry.agent_registry import get_registered_agent
from app.registry.capability_schema_registry import get_capability_schema
from app.services.dynamic_adversarial_test_generator import (
    generate_dynamic_adversarial_tests,
)
from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
)
from app.services.adversarial_response_adapter import (
    adapt_adversarial_exception,
)


ALLOWED_TEST_AGENT = "metadata_agent_001"

SUPPORTED_SCENARIOS = (
    "missing_",
    "invalid_",
    "empty_",
)


def expected_error_code(case):
    """
    Derive the expected validation code from
    the trusted schema and generated scenario.
    """

    schema = get_capability_schema(
        case["agent_id"],
        case["capability"],
    )

    if not schema:
        raise ValueError("Capability schema not found")

    scenario = case["scenario"]
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for field in required:
        definition = properties.get(field, {})

        if scenario == f"missing_{field}":
            return "INVALID_INPUT"

        if scenario == f"invalid_{field}_type":
            return "INVALID_INPUT"

        if (
            scenario == f"empty_{field}"
            and definition.get("type") == "string"
            and definition.get("minLength", 0) > 0
        ):
            return "INVALID_INPUT"

    raise ValueError(
        f"Unsupported generated scenario: {scenario}"
    )


def run_dynamic_tests(agent_id):
    """
    Execute only trusted generated cases against
    the explicitly allowlisted local Metadata Agent.
    """

    if agent_id != ALLOWED_TEST_AGENT:
        raise ValueError(
            "Phase 15.4 execution is restricted "
            "to the local Metadata Agent."
        )

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError("Agent is not registered")

    if manifest.execution_type != "local":
        raise ValueError("Only local execution is supported")

    if manifest.status != "active":
        raise ValueError("Agent is not active")

    tests = generate_dynamic_adversarial_tests(agent_id)

    if not tests:
        raise ValueError("No generated tests available")

    results = []

    for case in tests:

        start = time.perf_counter()

        status = "inconclusive"
        observation = ""
        actual_error_code = None

        try:
            if case["agent_id"] != agent_id:
                raise ValueError("Agent ID mismatch")

            if case["capability"] not in manifest.capabilities:
                raise ValueError("Capability not registered")

            if case.get("execution_mode") != "generation_only":
                raise ValueError("Unexpected execution mode")

            if case.get("expected_outcome") != "rejected":
                raise ValueError("Unexpected test expectation")

            if not case["scenario"].startswith(
                SUPPORTED_SCENARIOS
            ):
                raise ValueError("Scenario not allowlisted")

            expected_code = expected_error_code(case)

        except (ValueError, KeyError, TypeError) as exc:
            status = "error"
            observation = f"Test configuration error: {exc}"

        else:
            try:
                # The supervisor still enforces its
                # existing approval and routing checks.
                response = execute_supervisor_request(
                    capability=case["capability"],
                    payload=case["input"].copy(),
                    preferred_agent_id=agent_id,
                )

                # Every generated test expects rejection.
                # Successful execution must not pass.
                status = "failed"
                observation = (
                    "Invalid input was not rejected; "
                    "supervisor returned normally."
                )

            except Exception as exc:
                adapted = adapt_adversarial_exception(exc)

                actual_error_code = adapted.get("error_code")

                if (
                    adapted.get("status") == "rejected"
                    and adapted.get("source")
                    == "agent_input_validator"
                    and actual_error_code == expected_code
                ):
                    status = "passed"
                    observation = (
                        "Expected structured rejection confirmed"
                    )

                else:
                    status = "inconclusive"
                    observation = (
                        "Expected rejection was not verified. "
                        f"Observed status={adapted.get('status')}, "
                        f"code={actual_error_code}, "
                        f"source={adapted.get('source')}"
                    )

        elapsed = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        results.append({
            "test_id": case["test_id"],
            "agent_id": agent_id,
            "capability": case["capability"],
            "scenario": case["scenario"],
            "status": status,
            "passed": status == "passed",
            "expected_outcome": "rejected",
            "actual_error_code": actual_error_code,
            "observation": observation,
            "execution_time_ms": elapsed,
            "tested_at": datetime.now(
                timezone.utc
            ).isoformat(),
        })

        print(
            f"{case['test_id']} | "
            f"{case['capability']} | "
            f"{case['scenario']} | "
            f"{status.upper()}"
        )

    counts = Counter(
        item["status"] for item in results
    )

    total = len(results)
    passed = counts["passed"]
    failed = counts["failed"]
    errors = counts["error"]
    inconclusive = counts["inconclusive"]

    report_status = (
        "passed" if passed == total
        else "failed" if failed
        else "error" if errors
        else "incomplete"
    )

    return {
        "agent_id": agent_id,
        "assurance_type": "dynamic_adversarial",
        "phase": "15.4",
        "status": report_status,
        "passed": passed == total,
        "total_tests": total,
        "passed_tests": passed,
        "failed_tests": failed,
        "error_tests": errors,
        "inconclusive_tests": inconclusive,
        "results": results,
    }


if __name__ == "__main__":

    report = run_dynamic_tests(
        ALLOWED_TEST_AGENT
    )

    print("\nPHASE 15.4 EXECUTION SUMMARY")
    print("=" * 45)

    for key in (
        "agent_id",
        "status",
        "total_tests",
        "passed_tests",
        "failed_tests",
        "error_tests",
        "inconclusive_tests",
    ):
        print(f"{key}: {report[key]}")

    print("\nCOMPLETE JSON REPORT")
    print(json.dumps(report, indent=4))
