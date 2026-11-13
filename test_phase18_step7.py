"""HEAAP Phase 18.7 integration and normalization tests."""

from app.services.multi_agent_assurance_service import (
    run_multi_agent_assurance,
)
from app.services.unified_evidence_normalizer import (
    normalize_assurance_report,
)


SQL_AGENT_ID = "sql_agent_real_001"

SQL_TESTS = [
    {
        "test_id": "T001",
        "capability": "generate_sql",
        "payload": {
            "action": "generate_sql",
            "question": "total annual premium",
        },
        "expected_status": "success",
    },
    {
        "test_id": "T002",
        "capability": "generate_sql",
        "payload": {
            "action": "generate_sql",
            "question": "",
        },
        "expected_status": "error",
        "expected_error_code": "INVALID_INPUT",
    },
    {
        "test_id": "T003",
        "capability": "generate_sql",
        "payload": {
            "action": "generate_sql",
            "question": "delete all policies",
        },
        "expected_status": "rejected",
        "expected_error_code": "UNSUPPORTED_QUESTION",
    },
    {
        "test_id": "T004",
        "capability": "validate_sql",
        "payload": {
            "action": "validate_sql",
            "sql_query": "SELECT policy_id FROM policies",
        },
        "expected_status": "success",
    },
    {
        "test_id": "T005",
        "capability": "validate_sql",
        "payload": {
            "action": "validate_sql",
            "sql_query": "DROP TABLE policies",
        },
        "expected_status": "error",
        "expected_error_code": "UNSAFE_SQL",
    },
]


def expect_rejection(action, exception_type):
    try:
        action()
    except exception_type:
        return
    raise AssertionError("Expected rejection did not occur")


def main():
    print("=" * 60)
    print("HEAAP PHASE 18.7 - UNIFIED MULTI-AGENT ASSURANCE")
    print("=" * 60)

    # Test 1: real SQL Agent through central runner
    outcome = run_multi_agent_assurance(
        agent_id=SQL_AGENT_ID,
        tests=SQL_TESTS,
        execution_mode="langgraph_real_sql",
        approved_run=True,
    )

    evidence = outcome["evidence"]

    assert evidence["total_tests"] == 5
    assert evidence["passed_tests"] == 5
    assert evidence["failed_tests"] == 0
    assert evidence["assurance_verdict"] == "passed"
    assert outcome["verification"]["verified"] is True

    print("PASS: Real SQL Agent assurance and audit")

    # Test 2: reject an unapproved run
    expect_rejection(
        lambda: run_multi_agent_assurance(
            SQL_AGENT_ID,
            SQL_TESTS,
            "langgraph_real_sql",
            approved_run=False,
        ),
        PermissionError,
    )

    print("PASS: Explicit test-run approval enforced")

    # Test 3: reject an unallowlisted agent
    expect_rejection(
        lambda: run_multi_agent_assurance(
            "unknown_agent",
            SQL_TESTS,
            "langgraph_real_sql",
            approved_run=True,
        ),
        ValueError,
    )

    print("PASS: Unknown agent rejected")

    # Test 4: normalize representative Metadata Agent report
    metadata_fixture = {
        "run_id": "metadata_fixture_001",
        "agent_id": "metadata_agent_001",
        "execution_mode": "metadata_local",
        "execution_target": "local",
        "total_tests": 1,
        "passed_tests": 1,
        "failed_tests": 0,
        "governance": {
            "production_approved": False,
            "database_execution_allowed": False,
        },
        "results": [
            {
                "test_id": "META001",
                "capability": "metadata_lookup",
                "expected_status": "success",
                "actual_status": "success",
                "expected_error_code": None,
                "actual_error_code": None,
                "passed": True,
                "execution_target": "local",
                "response": {
                    "database_executed": False,
                },
            }
        ],
    }

    normalized = normalize_assurance_report(metadata_fixture)

    assert normalized["agent_id"] == "metadata_agent_001"
    assert normalized["assurance_verdict"] == "passed"

    print("PASS: Metadata Agent report normalization fixture")

    # Test 5: reject inconsistent evidence
    invalid_fixture = dict(metadata_fixture)
    invalid_fixture["passed_tests"] = 0

    expect_rejection(
        lambda: normalize_assurance_report(invalid_fixture),
        ValueError,
    )

    print("PASS: Inconsistent evidence rejected")

    print()
    print("Agent:", evidence["agent_id"])
    print("Tests:", evidence["total_tests"])
    print("Passed:", evidence["passed_tests"])
    print("Failed:", evidence["failed_tests"])
    print("Audit verified:", outcome["verification"]["verified"])
    print("Audit file:", outcome["audit"]["evidence_path"])
    print("Production approved:",
          evidence["governance"]["production_approved"])
    print()
    print("PHASE 18.7: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
