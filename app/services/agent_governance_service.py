"""
HEAAP Phase 16.6
Read-only Agent Governance Assessment.

Does not activate agents or grant production approval.
"""

from datetime import datetime, timezone

from app.registry.agent_registry import get_registered_agent
from app.registry.dynamic_capability_registry import (
    get_dynamic_capability_schemas,
)


def assess_agent_governance(agent_id, assurance_report):

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError("Agent is not registered")

    if not isinstance(assurance_report, dict):
        raise ValueError("Assurance report must be a dictionary")

    schemas = get_dynamic_capability_schemas(agent_id)

    if set(schemas) != set(manifest.capabilities):
        raise ValueError("Capability schema coverage is incomplete")

    if assurance_report.get("agent_id") != agent_id:
        raise ValueError("Assurance report agent mismatch")

    if assurance_report.get("phase") != "16.5":
        raise ValueError("Unsupported assurance report phase")

    if assurance_report.get("execution_target") != "mock_local":
        raise ValueError("Unexpected execution target")

    results = assurance_report.get("results")

    if not isinstance(results, list) or not results:
        raise ValueError("Assurance results are missing")

    expected_count = assurance_report.get("total_tests")

    if type(expected_count) is not int or expected_count != len(results):
        raise ValueError("Test count mismatch")

    ids = [r.get("test_id") for r in results]

    if any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("Invalid test identifiers")

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate test identifiers")

    valid_statuses = {
        "passed", "failed", "error", "inconclusive"
    }

    if any(
        not isinstance(r, dict)
        or r.get("agent_id") != agent_id
        or r.get("capability") not in manifest.capabilities
        or r.get("status") not in valid_statuses
        for r in results
    ):
        raise ValueError("Invalid assurance result")

    passed = sum(r["status"] == "passed" for r in results)
    failed = sum(r["status"] == "failed" for r in results)
    errors = sum(r["status"] == "error" for r in results)
    inconclusive = sum(
        r["status"] == "inconclusive" for r in results
    )

    all_passed = (
        passed == len(results)
        and failed == 0
        and errors == 0
        and inconclusive == 0
        and assurance_report.get("status") == "passed"
        and assurance_report.get("passed") is True
        and assurance_report.get("passed_tests") == passed
        and assurance_report.get("failed_tests") == failed
        and assurance_report.get("error_tests") == errors
        and assurance_report.get("inconclusive_tests") == inconclusive
    )

    return {
        "platform": "HEAAP",
        "phase": "16.6",
        "agent_id": agent_id,
        "assessed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "registry_status": manifest.status,
        "execution_target": "mock_local",
        "assurance_checks_passed": all_passed,
        "approval_eligibility": (
            "requires_real_agent_evidence"
            if all_passed
            else "blocked"
        ),
        "production_approved": False,
        "activation_performed": False,
        "reason": (
            "Mock tests passed, but real-agent assurance "
            "and authorized human review are required."
            if all_passed
            else "Assurance evidence did not pass all checks."
        ),
    }
