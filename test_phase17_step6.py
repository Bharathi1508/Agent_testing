"""
HEAAP Phase 17.6 Verification.

Uses synthetic evidence only.
Does not invoke an agent or Databricks.
"""

import copy
import json

from app.services.assurance_evidence_service import (
    assess_assurance_evidence,
)
from app.services.assurance_audit_service import (
    record_assurance_evidence,
    verify_saved_evidence,
)


def create_sample_report():

    results = []

    for index in range(1, 11):
        results.append({
            "test_id": f"AUTO_ADV_{index:03d}",
            "agent_id": "sql_agent_001",
            "capability": (
                "generate_sql"
                if index <= 5
                else "validate_sql"
            ),
            "scenario": "synthetic_input_validation",
            "expected_outcome": "rejected",
            "actual_status": "rejected",
            "actual_error_code": "INVALID_INPUT",
            "execution_target": "langgraph_local",
            "status": "passed",
            "passed": True,
            "observation": "Synthetic test result",
            "execution_time_ms": 1.0,
        })

    return {
        "platform": "HEAAP",
        "phase": "17.5",
        "assurance_type": "unified_adversarial",
        "agent_id": "sql_agent_001",
        "execution_mode": "langgraph_demo",
        "status": "passed",
        "total_tests": 10,
        "passed_tests": 10,
        "failed_tests": 0,
        "error_tests": 0,
        "inconclusive_tests": 0,
        "not_executed_tests": 0,
        "production_approved": False,
        "results": results,
    }


def main():

    report = create_sample_report()

    assessment = assess_assurance_evidence(report)

    assert assessment["passed_tests"] == 10
    assert assessment["production_approved"] is False
    assert assessment["activation_performed"] is False
    assert assessment["governance_decision"] == (
        "development_review_only"
    )

    print("PASSED: Evidence assessment")

    saved = record_assurance_evidence(report)

    print("PASSED: Evidence recorded")

    assert verify_saved_evidence(
        saved["evidence_path"],
        saved["audit_path"],
    )

    print("PASSED: Saved evidence hashes verified")

    changed = copy.deepcopy(report)
    changed["passed_tests"] = 9

    try:
        assess_assurance_evidence(changed)
    except ValueError:
        print("PASSED: Inconsistent counts rejected")
    else:
        raise AssertionError(
            "Inconsistent report was accepted"
        )

    dry_run = copy.deepcopy(report)
    dry_run["execution_mode"] = "databricks_dry_run"

    try:
        assess_assurance_evidence(dry_run)
    except ValueError:
        print("PASSED: False dry-run pass rejected")
    else:
        raise AssertionError(
            "Dry-run was incorrectly accepted"
        )

    print("\nPHASE 17.6 EXECUTION SUMMARY")
    print("=" * 55)
    print("Agent:", assessment["agent_id"])
    print("Tests:", assessment["total_tests"])
    print("Governance:", assessment["governance_decision"])
    print("Production approved:", assessment["production_approved"])
    print("Evidence file:", saved["evidence_path"])
    print("Audit file:", saved["audit_path"])

    print("\nPHASE 17.6: ALL 5 CHECKS PASSED")


if __name__ == "__main__":
    main()
