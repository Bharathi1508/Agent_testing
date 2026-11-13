"""
HEAAP Phase 17.5
Unified Multi-Framework Adversarial Runner.

Supported:
- Local Metadata Agent (explicit invocation)
- LangGraph SQL demonstration agent
- Databricks dry-run only

No automatic activation or live Databricks invocation.
"""

import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.real_agent_contract import (
    AgentExecutionRequest,
)
from app.registry.agent_registry import get_registered_agent


ALLOWED_TARGETS = {
    ("metadata_agent_001", "metadata_local"),
    ("sql_agent_001", "langgraph_demo"),
}

MAX_TESTS = 100


def select_adapter(agent_id, execution_mode):
    """
    Resolve only trusted, explicitly supported adapters.
    """

    if execution_mode == "databricks_dry_run":
        from app.adapters.databricks_agent_adapter import (
            DatabricksAgentAdapter,
        )
        return DatabricksAgentAdapter(dry_run=True)

    if (agent_id, execution_mode) not in ALLOWED_TARGETS:
        raise PermissionError(
            "Agent and execution mode are not approved"
        )

    if execution_mode == "metadata_local":
        from app.adapters.local_metadata_adapter import (
            LocalMetadataAdapter,
        )
        return LocalMetadataAdapter()

    if execution_mode == "langgraph_demo":
        from app.adapters.langgraph_agent_adapter import (
            LangGraphAgentAdapter,
        )
        return LangGraphAgentAdapter()

    raise ValueError("Unsupported execution mode")


def evaluate_result(test, result):
    """
    Assess observed behavior independently of the adapter.

    A dry-run is never a passing test.
    """

    if result.status == "not_executed":
        return "not_executed", "No agent invocation occurred"

    if result.status == "response_received":
        return (
            "inconclusive",
            "Response received but not protocol-normalized",
        )

    expected = test["expected_outcome"]

    if expected == "rejected":
        if (
            result.status == "rejected"
            and result.error_code == "INVALID_INPUT"
        ):
            return "passed", "Expected input rejection confirmed"

        if result.status == "success":
            return "failed", "Invalid input was accepted"

        return (
            "inconclusive",
            "Expected structured input rejection not confirmed",
        )

    if expected == "success":
        if result.status == "success":
            return "passed", "Expected success confirmed"

        if result.status == "rejected":
            return "failed", "Valid input was rejected"

        return "inconclusive", "Expected success not confirmed"

    return "error", "Unsupported expected outcome"


def run_unified_tests(
    agent_id,
    tests,
    execution_mode,
    *,
    approved_run=False,
):
    """
    Execute only an explicitly requested test run.

    This approval flag is a development control,
    not production-grade authorization.
    """

    if approved_run is not True:
        raise PermissionError(
            "Explicit test-run approval is required"
        )

    # HEAAP_PHASE18_5_REAL_SQL_DISPATCH
    if execution_mode == "langgraph_real_sql":
        if agent_id != "sql_agent_real_001":
            raise ValueError("Agent is not allowlisted")

        from app.services.phase18_real_sql_runner import (
            run_real_sql_tests,
        )

        return run_real_sql_tests(
            agent_id=agent_id,
            tests=tests,
            execution_mode=execution_mode,
            approved_run=False,
        )

    if not isinstance(tests, list) or not tests:
        raise ValueError("Tests must be a nonempty list")

    if len(tests) > MAX_TESTS:
        raise ValueError("Too many tests")

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError("Agent is not registered")

    if execution_mode == "metadata_local":
        if manifest.execution_type != "local":
            raise ValueError("Expected local agent")
        if manifest.status != "active":
            raise PermissionError("Metadata Agent must be active")

    elif execution_mode == "langgraph_demo":
        if manifest.execution_type != "local":
            raise ValueError("Expected local LangGraph agent")
        if manifest.framework.lower() != "langgraph":
            raise ValueError("Expected LangGraph framework")
        if manifest.status != "inactive":
            raise PermissionError(
                "Demo SQL Agent must remain inactive"
            )

    elif execution_mode == "databricks_dry_run":
        if manifest.execution_type != "databricks":
            raise ValueError("Expected Databricks agent")

    else:
        raise ValueError("Unsupported execution mode")

    # Only the trusted adapter is selected.
    adapter = select_adapter(agent_id, execution_mode)

    results = []
    seen_ids = set()

    for test in tests:

        started = time.perf_counter()

        test_id = test.get("test_id")
        capability = test.get("capability")
        payload = test.get("input")
        expected = test.get("expected_outcome")

        if (
            not isinstance(test_id, str)
            or not test_id
            or test_id in seen_ids
            or test.get("agent_id") != agent_id
            or capability not in manifest.capabilities
            or not isinstance(payload, dict)
            or expected not in ("rejected", "success")
        ):
            raise ValueError(
                "Invalid test definition or duplicate test ID"
            )

        seen_ids.add(test_id)

        request = AgentExecutionRequest(
            agent_id=agent_id,
            capability=capability,
            payload=payload.copy(),
            test_id=test_id,
        )

        actual_status = None
        error_code = None
        target = execution_mode

        try:
            execution = adapter.execute(request)

            if (
                execution.agent_id != agent_id
                or execution.capability != capability
                or execution.test_id != test_id
            ):
                raise ValueError(
                    "Adapter returned mismatched execution identity"
                )

            actual_status = execution.status
            error_code = execution.error_code
            target = execution.execution_target

            status, observation = evaluate_result(
                test, execution
            )

        except Exception as exc:
            # An exception is not automatically a successful
            # rejection by the agent.
            status = "error"
            observation = (
                f"Adapter exception: {type(exc).__name__}"
            )

        elapsed = round(
            (time.perf_counter() - started) * 1000,
            2,
        )

        results.append({
            "test_id": test_id,
            "agent_id": agent_id,
            "capability": capability,
            "scenario": test.get("scenario"),
            "expected_outcome": expected,
            "actual_status": actual_status,
            "actual_error_code": error_code,
            "execution_target": target,
            "status": status,
            "passed": status == "passed",
            "observation": observation,
            "execution_time_ms": elapsed,
        })

        print(
            test_id,
            "|",
            capability,
            "|",
            status.upper(),
        )

    counts = Counter(r["status"] for r in results)

    total = len(results)
    passed = counts["passed"]
    failed = counts["failed"]
    errors = counts["error"]
    inconclusive = counts["inconclusive"]
    not_executed = counts["not_executed"]

    if failed:
        overall = "failed"
    elif errors:
        overall = "error"
    elif not_executed:
        overall = "not_executed"
    elif inconclusive:
        overall = "incomplete"
    elif passed == total:
        overall = "passed"
    else:
        overall = "incomplete"

    return {
        "platform": "HEAAP",
        "phase": "17.5",
        "assurance_type": "unified_adversarial",
        "agent_id": agent_id,
        "execution_mode": execution_mode,
        "status": overall,
        "total_tests": total,
        "passed_tests": passed,
        "failed_tests": failed,
        "error_tests": errors,
        "inconclusive_tests": inconclusive,
        "not_executed_tests": not_executed,
        "production_approved": False,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "results": results,
    }


def save_unified_report(report):
    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d_%H%M%S_%f")

    path = report_dir / (
        f"phase17_5_{report['agent_id']}_{stamp}.json"
    )

    with path.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    return path
