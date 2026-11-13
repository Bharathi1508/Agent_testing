"""HEAAP Phase 19.3 - Dynamic assurance integration tests."""

from app.services.external_agent_assurance_orchestrator import (
    ExternalAgentAssuranceOrchestrator,
)


def make_agent(agent_id, endpoint, capabilities, approved=True):
    manifest = {
        "agent_id": agent_id,
        "endpoint_name": endpoint,
        "capabilities": capabilities,
    }

    review = {
        "agent": {
            "agent_id": agent_id,
            "endpoint_name": endpoint,
            "declared_capabilities": capabilities,
            "manifest_valid": True,
            "capabilities_verified": approved,
            "trust_status": (
                "verified" if approved else "unverified"
            ),
            "production_approved": False,
        },
        "discovered_endpoint": {
            "provider": "databricks",
            "endpoint_name": endpoint,
        },
        "review_status": (
            "approved" if approved else "pending_manual_review"
        ),
        "execution_authorized": approved,
        "production_approved": False,
    }

    return manifest, review


def expect_blocked(fn, label, error_type):
    try:
        fn()
    except error_type:
        print(label, "PASS")
        return

    raise AssertionError(label + " unexpectedly succeeded")


def main():
    print("HEAAP PHASE 19.3 - DYNAMIC ASSURANCE INTEGRATION")
    print("=" * 55)

    orchestrator = ExternalAgentAssuranceOrchestrator()

    sql_manifest, sql_review = make_agent(
        "external_sql_agent_001",
        "heaap-sql-agent",
        ["generate_sql", "validate_sql"],
    )

    orchestrator.register_reviewed_agent(
        sql_manifest,
        sql_review,
    )

    # One supported mock SQL test.
    tests = [
        {
            "test_id": "EXT001",
            "capability": "generate_sql",
            "payload": {
                "question": "total annual premium",
            },
            "expected_status": "success",
        },
        {
            "test_id": "EXT002",
            "capability": "generate_sql",
            "payload": {
                "question": "delete all policies",
            },
            "expected_status": "rejected",
            "expected_error_code": "UNSUPPORTED_QUESTION",
        },
    ]

    report = orchestrator.run_assurance(
        "generate_sql",
        tests,
        approved_run=True,
    )

    assert report["agent_id"] == "external_sql_agent_001"
    assert report["total_tests"] == 2
    assert report["passed_tests"] == 2
    assert report["failed_tests"] == 0
    assert report["verdict"] == "passed"

    print("Capability routing: PASS")
    print("Onboarding approval gate: PASS")
    print("Mock contract testing: PASS")
    print("Unified assurance result: PASS")

    expect_blocked(
        lambda: orchestrator.run_assurance(
            "generate_sql",
            tests,
            approved_run=False,
        ),
        "Missing run approval blocked:",
        PermissionError,
    )

    expect_blocked(
        lambda: orchestrator.run_assurance(
            "generate_sql",
            [
                {
                    "test_id": "BAD001",
                    "capability": "detect_fraud",
                    "payload": {},
                    "expected_status": "success",
                }
            ],
            approved_run=True,
        ),
        "Mismatched capability blocked:",
        ValueError,
    )

    pending_manifest, pending_review = make_agent(
        "pending_agent_001",
        "pending-agent",
        ["generate_sql"],
        approved=False,
    )

    expect_blocked(
        lambda: orchestrator.register_reviewed_agent(
            pending_manifest,
            pending_review,
        ),
        "Pending agent blocked:",
        PermissionError,
    )

    assert report["governance"]["production_approved"] is False
    assert report["governance"]["live_endpoint_invoked"] is False

    print()
    print("Agent:", report["agent_id"])
    print("Capability:", report["capability"])
    print("Tests:", report["total_tests"])
    print("Passed:", report["passed_tests"])
    print("Failed:", report["failed_tests"])
    print("Verdict:", report["verdict"])
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print()
    print("PHASE 19.3: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
