"""
HEAAP Phase 16.5
Automatic Assurance Orchestrator

Scope:
- Explicitly allowlisted mock SQL Agent
- Dynamic schema-generated negative tests
- No real SQL execution
- No Databricks endpoint calls
- No automatic agent activation
"""

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.registry.agent_registry import get_registered_agent
from app.registry.dynamic_capability_registry import (
    get_dynamic_capability_schemas,
)
from app.services.auto_adversarial_test_generator import (
    generate_agent_adversarial_tests,
)
from app.adapters.agent_execution_adapter import (
    execute_approved_mock_test,
    AdapterExecutionError,
)


ALLOWED_AGENT = "sql_agent_001"

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def validate_generated_test(test, schema):
    """
    Validate that a generated test matches a
    supported negative-input scenario.
    """

    required = schema["required"]
    properties = schema["properties"]

    field = test.get("field_under_test")
    scenario = test.get("scenario")
    payload = test.get("input")

    if field not in required:
        raise ValueError("Field is not required")

    if not isinstance(payload, dict):
        raise ValueError("Test input must be an object")

    if test.get("expected_outcome") != "rejected":
        raise ValueError("Unsupported expected outcome")

    definition = properties[field]
    field_type = definition["type"]

    if scenario == f"missing_{field}":
        if field in payload:
            raise ValueError("Missing-field test contains the field")

    elif scenario == f"invalid_{field}_type":
        if field not in payload:
            raise ValueError("Invalid-type test is missing its field")

        value = payload[field]

        type_checks = {
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: type(v) is int,
            "number": lambda v: type(v) in (int, float),
            "boolean": lambda v: type(v) is bool,
            "array": lambda v: isinstance(v, list),
            "object": lambda v: isinstance(v, dict),
        }

        if type_checks[field_type](value):
            raise ValueError("Value is not an invalid type")

    elif scenario == f"empty_{field}":
        if field_type != "string":
            raise ValueError("Empty-string scenario is unsupported")

        if definition.get("minLength", 0) < 1:
            raise ValueError("Field does not require nonempty string")

        if payload.get(field) != "":
            raise ValueError("Expected empty string")

    else:
        raise ValueError(f"Unsupported scenario: {scenario}")


def run_automatic_assurance(agent_id):
    """
    Execute generated tests only against the
    explicitly allowlisted mock SQL Agent.
    """

    if agent_id != ALLOWED_AGENT:
        raise ValueError(
            "Automatic execution is restricted "
            "to sql_agent_001"
        )

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError("Agent not registered")

    if manifest.status != "inactive":
        raise ValueError(
            "Onboarding assurance requires inactive agent"
        )

    if manifest.execution_type != "local":
        raise ValueError(
            "Only local mock execution is supported"
        )

    schemas = get_dynamic_capability_schemas(agent_id)

    tests = generate_agent_adversarial_tests(agent_id)

    if not tests:
        raise ValueError("No generated tests")

    results = []

    for test in tests:

        start = time.perf_counter()
        status = "inconclusive"
        observation = ""
        actual_error_code = None

        try:
            if test["agent_id"] != agent_id:
                raise ValueError("Agent ID mismatch")

            capability = test["capability"]

            if capability not in manifest.capabilities:
                raise ValueError("Capability not registered")

            if test.get("execution_mode") != "generation_only":
                raise ValueError("Unexpected test execution mode")

            validate_generated_test(
                test,
                schemas[capability],
            )

        except (ValueError, KeyError, TypeError) as exc:
            status = "error"
            observation = f"Test configuration error: {exc}"

        else:
            try:
                response = execute_approved_mock_test(
                    agent_id,
                    test["input"],
                    approved_test=True,
                )

                if not isinstance(response, dict):
                    status = "inconclusive"
                    observation = "Unexpected response format"

                else:
                    actual_error_code = response.get("error_code")

                    if (
                        response.get("status") == "rejected"
                        and actual_error_code == "INVALID_INPUT"
                    ):
                        status = "passed"
                        observation = (
                            "Expected structured input rejection confirmed"
                        )

                    elif response.get("status") == "success":
                        status = "failed"
                        observation = (
                            "Invalid input was unexpectedly accepted"
                        )

                    else:
                        status = "inconclusive"
                        observation = (
                            "Expected input rejection was not confirmed"
                        )

            except AdapterExecutionError as exc:
                status = "error"
                observation = f"Adapter error: {exc}"

            except Exception as exc:
                status = "inconclusive"
                observation = (
                    f"Unexpected execution exception: "
                    f"{type(exc).__name__}"
                )

        elapsed = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        results.append({
            "test_id": test["test_id"],
            "agent_id": agent_id,
            "capability": test["capability"],
            "scenario": test["scenario"],
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
            test["test_id"],
            "|",
            test["capability"],
            "|",
            test["scenario"],
            "|",
            status.upper(),
        )

    counts = Counter(
        result["status"] for result in results
    )

    total = len(results)
    passed = counts["passed"]
    failed = counts["failed"]
    errors = counts["error"]
    inconclusive = counts["inconclusive"]

    overall_status = (
        "passed" if passed == total
        else "failed" if failed
        else "error" if errors
        else "incomplete"
    )

    return {
        "platform": "HEAAP",
        "agent_id": agent_id,
        "assurance_type": "automatic_adversarial",
        "phase": "16.5",
        "execution_target": "mock_local",
        "status": overall_status,
        "passed": passed == total,
        "total_tests": total,
        "passed_tests": passed,
        "failed_tests": failed,
        "error_tests": errors,
        "inconclusive_tests": inconclusive,
        "results": results,
    }


def save_assurance_report(report):

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d_%H%M%S_%f")

    path = REPORT_DIR / (
        f"phase16_5_{report['agent_id']}_{timestamp}.json"
    )

    with path.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    return path


if __name__ == "__main__":

    report = run_automatic_assurance(ALLOWED_AGENT)

    report_path = save_assurance_report(report)

    print("\nHEAAP PHASE 16.5 SUMMARY")
    print("=" * 50)

    for key in (
        "agent_id",
        "execution_target",
        "status",
        "total_tests",
        "passed_tests",
        "failed_tests",
        "error_tests",
        "inconclusive_tests",
    ):
        print(f"{key}: {report[key]}")

    print("\nReport saved to:", report_path)
