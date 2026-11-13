
"""
HEAAP Phase 18.5
Real SQL Agent Assurance Runner

- Supports the registered Real LangGraph SQL Agent
- Executes local assurance tests through RealSQLAgentAdapter
- Validates test definitions
- Generates structured assurance reports
- Does not execute SQL against Databricks
- Does not approve agents for production
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.adapters.real_agent_contract import AgentExecutionRequest
from app.adapters.real_sql_agent_adapter import RealSQLAgentAdapter
from app.registry.agent_registry import get_registered_agent
from app.registry.dynamic_capability_registry import (
    get_dynamic_capability_schemas,
)


AGENT_ID = "sql_agent_real_001"
EXECUTION_MODE = "langgraph_real_sql"
EXECUTION_TARGET = "langgraph_local"

REPORT_DIR = Path("reports") / "phase18_4"


def validate_test_definition(test, index, schemas):
    """Validate an assurance test without executing it."""

    if not isinstance(test, dict):
        raise ValueError(f"Test {index} must be an object")

    test_id = test.get("test_id", f"T{index:03d}")

    if not isinstance(test_id, str) or not test_id.strip():
        raise ValueError(f"Invalid test_id at position {index}")

    capability = test.get("capability")

    if not isinstance(capability, str) or capability not in schemas:
        raise ValueError(
            f"Unregistered capability in test {test_id}: {capability}"
        )

    payload = test.get("payload")

    if not isinstance(payload, dict):
        raise ValueError(
            f"Payload must be an object in test {test_id}"
        )

    expected_status = test.get("expected_status")

    if expected_status not in {"success", "error", "rejected"}:
        raise ValueError(
            f"Invalid expected_status in test {test_id}"
        )

    expected_error_code = test.get("expected_error_code")

    if (
        expected_error_code is not None
        and not isinstance(expected_error_code, str)
    ):
        raise ValueError(
            f"Invalid expected_error_code in test {test_id}"
        )

    return {
        "test_id": test_id,
        "capability": capability,
        "payload": payload,
        "expected_status": expected_status,
        "expected_error_code": expected_error_code,
    }


def run_real_sql_tests(
    agent_id,
    tests,
    execution_mode=EXECUTION_MODE,
    approved_run=False,
):
    """
    Execute local adversarial tests for the Real SQL Agent.

    This is development-only assurance testing.
    """

    if agent_id != AGENT_ID:
        raise ValueError(
            "Agent is not allowlisted for the Real SQL runner"
        )

    if execution_mode != EXECUTION_MODE:
        raise ValueError(
            "Unsupported execution mode"
        )

    if approved_run:
        raise ValueError(
            "Elevated or production approval is not supported"
        )

    agent = get_registered_agent(agent_id)

    if agent is None:
        raise ValueError("Agent is not registered")

    if agent.status != "inactive":
        raise ValueError(
            "Real SQL Agent must remain inactive for this phase"
        )

    schemas = get_dynamic_capability_schemas(agent_id)

    if not isinstance(schemas, dict):
        raise ValueError(
            "Capability registry returned an invalid schema structure"
        )

    if not {"generate_sql", "validate_sql"}.issubset(schemas):
        raise ValueError(
            "Required Real SQL Agent capabilities are not registered"
        )

    if not isinstance(tests, list) or not tests:
        raise ValueError(
            "Tests must be a nonempty list"
        )

    validated_tests = []
    seen_ids = set()

    for index, test in enumerate(tests, start=1):
        validated = validate_test_definition(
            test,
            index,
            schemas,
        )

        test_id = validated["test_id"]

        if test_id in seen_ids:
            raise ValueError(
                f"Duplicate test_id: {test_id}"
            )

        seen_ids.add(test_id)
        validated_tests.append(validated)

    adapter = RealSQLAgentAdapter()
    results = []

    for test in validated_tests:

        request = AgentExecutionRequest(
            agent_id=agent_id,
            capability=test["capability"],
            payload=test["payload"],
            test_id=test["test_id"],
        )

        try:
            response = adapter.execute(request)

            actual_status = response.status
            actual_error_code = response.error_code
            response_payload = response.response
            execution_target = response.execution_target

        except Exception:
            actual_status = "error"
            actual_error_code = "ADAPTER_EXECUTION_ERROR"
            response_payload = {
                "message": "Local adapter execution failed",
                "database_executed": False,
            }
            execution_target = EXECUTION_TARGET

        passed = (
            actual_status == test["expected_status"]
            and (
                test["expected_error_code"] is None
                or actual_error_code == test["expected_error_code"]
            )
        )

        results.append({
            "test_id": test["test_id"],
            "capability": test["capability"],
            "expected_status": test["expected_status"],
            "actual_status": actual_status,
            "expected_error_code": test["expected_error_code"],
            "actual_error_code": actual_error_code,
            "passed": passed,
            "response": response_payload,
            "execution_target": execution_target,
        })

    passed_count = sum(
        1 for result in results if result["passed"]
    )

    return {
        "phase": "18.5",
        "run_id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "execution_mode": execution_mode,
        "execution_target": EXECUTION_TARGET,
        "governance": {
            "decision": "development_review_only",
            "production_approved": False,
            "database_execution_allowed": False,
        },
        "total_tests": len(results),
        "passed_tests": passed_count,
        "failed_tests": len(results) - passed_count,
        "results": results,
    }


def save_real_sql_report(report):
    """Save a unique JSON assurance report."""

    if not isinstance(report, dict):
        raise ValueError("Report must be an object")

    if report.get("agent_id") != AGENT_ID:
        raise ValueError("Report agent ID mismatch")

    if report.get("execution_mode") != EXECUTION_MODE:
        raise ValueError("Report execution mode mismatch")

    if report.get("governance", {}).get("production_approved") is not False:
        raise ValueError("Production approval is not permitted")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    run_id = report.get("run_id")

    if not isinstance(run_id, str) or not run_id:
        raise ValueError("Report run_id is missing")

    path = REPORT_DIR / f"{AGENT_ID}_{run_id}.json"

    with path.open("x", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return str(path)