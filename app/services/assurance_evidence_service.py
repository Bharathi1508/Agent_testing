"""
HEAAP Phase 17.6
Assurance evidence validation and governance assessment.

Read-only assessment. No agent execution or activation.
"""

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone


VALID_STATUSES = {
    "passed",
    "failed",
    "error",
    "inconclusive",
    "not_executed",
}

COUNT_FIELDS = {
    "passed": "passed_tests",
    "failed": "failed_tests",
    "error": "error_tests",
    "inconclusive": "inconclusive_tests",
    "not_executed": "not_executed_tests",
}


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def evidence_hash(report):
    """SHA-256 of the exact canonical report content."""
    return hashlib.sha256(
        canonical_json(report).encode("utf-8")
    ).hexdigest()


def validate_assurance_report(report):

    if not isinstance(report, dict):
        raise ValueError("Report must be a dictionary")

    if report.get("platform") != "HEAAP":
        raise ValueError("Unexpected platform")

    if report.get("phase") != "17.5":
        raise ValueError("Expected Phase 17.5 report")

    agent_id = report.get("agent_id")

    if not isinstance(agent_id, str) or not agent_id:
        raise ValueError("Invalid agent ID")

    mode = report.get("execution_mode")

    allowed_modes = {
        "metadata_local",
        "langgraph_demo",
        "databricks_dry_run",
    }

    if mode not in allowed_modes:
        raise ValueError("Unsupported execution mode")

    results = report.get("results")

    if not isinstance(results, list) or not results:
        raise ValueError("No assurance results found")

    total = report.get("total_tests")

    if type(total) is not int or total != len(results):
        raise ValueError("Total test count mismatch")

    if total > 100:
        raise ValueError("Test count exceeds Phase 17.5 limit")

    counts = Counter()
    seen_ids = set()

    for result in results:

        if not isinstance(result, dict):
            raise ValueError("Invalid test result")

        test_id = result.get("test_id")

        if not isinstance(test_id, str) or not test_id:
            raise ValueError("Missing test ID")

        if test_id in seen_ids:
            raise ValueError("Duplicate test ID")

        seen_ids.add(test_id)

        if result.get("agent_id") != agent_id:
            raise ValueError("Result agent mismatch")

        if not isinstance(result.get("capability"), str):
            raise ValueError("Invalid capability")

        status = result.get("status")

        if status not in VALID_STATUSES:
            raise ValueError("Invalid test status")

        if result.get("passed") is not (status == "passed"):
            raise ValueError("Inconsistent passed flag")

        if result.get("expected_outcome") not in (
            "rejected", "success"
        ):
            raise ValueError("Invalid expected outcome")

        target = result.get("execution_target")

        if not isinstance(target, str) or not target:
            raise ValueError("Missing execution target")

        if mode == "databricks_dry_run":
            if status != "not_executed":
                raise ValueError(
                    "Dry-run cannot be marked as executed"
                )
            if target != "databricks_dry_run":
                raise ValueError(
                    "Unexpected dry-run execution target"
                )

        if mode == "langgraph_demo":
            if target != "langgraph_local":
                raise ValueError(
                    "Unexpected LangGraph execution target"
                )

        if mode == "metadata_local":
            if target != "real_local_metadata":
                raise ValueError(
                    "Unexpected Metadata execution target"
                )

        counts[status] += 1

    for status, field in COUNT_FIELDS.items():
        reported = report.get(field)

        if type(reported) is not int:
            raise ValueError(f"Invalid count: {field}")

        if reported != counts[status]:
            raise ValueError(f"Count mismatch: {field}")

    if counts["failed"]:
        expected_overall = "failed"
    elif counts["error"]:
        expected_overall = "error"
    elif counts["not_executed"]:
        expected_overall = "not_executed"
    elif counts["inconclusive"]:
        expected_overall = "incomplete"
    elif counts["passed"] == total:
        expected_overall = "passed"
    else:
        expected_overall = "incomplete"

    if report.get("status") != expected_overall:
        raise ValueError("Overall status mismatch")

    if report.get("production_approved") is not False:
        raise ValueError(
            "Phase 17.5 must not approve production"
        )

    return counts


def assess_assurance_evidence(report):
    """
    Validate report consistency and produce a
    non-authorizing governance assessment.

    Does not establish trusted provenance.
    """

    counts = validate_assurance_report(report)

    total = report["total_tests"]
    mode = report["execution_mode"]

    all_passed = (
        counts["passed"] == total
        and report["status"] == "passed"
    )

    if not all_passed:
        decision = "blocked_or_incomplete"
        reason = (
            "Assurance contains failures, errors, "
            "inconclusive or unexecuted tests."
        )

    elif mode == "langgraph_demo":
        decision = "development_review_only"
        reason = (
            "Demonstration graph passed the reported tests. "
            "Production agent evidence is still required."
        )

    elif mode == "metadata_local":
        decision = "requires_human_review"
        reason = (
            "Reported local-agent tests passed. "
            "Trusted provenance and broader assurance "
            "are still required."
        )

    else:
        decision = "blocked_or_incomplete"
        reason = "Dry-run is not execution evidence."

    return {
        "platform": "HEAAP",
        "phase": "17.6",
        "agent_id": report["agent_id"],
        "execution_mode": mode,
        "evidence_sha256": evidence_hash(report),
        "assessed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_tests": total,
        "passed_tests": counts["passed"],
        "failed_tests": counts["failed"],
        "error_tests": counts["error"],
        "inconclusive_tests": counts["inconclusive"],
        "not_executed_tests": counts["not_executed"],
        "governance_decision": decision,
        "reason": reason,
        "evidence_provenance_verified": False,
        "production_approved": False,
        "activation_performed": False,
    }
