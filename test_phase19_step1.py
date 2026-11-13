"""HEAAP Phase 19.1 - External Agent Approval Gate Tests."""

from unittest.mock import patch

from app.services.external_agent_approval_gate import (
    validate_onboarding_approval,
    run_approved_external_tests,
)


MANIFEST = {
    "agent_id": "external_sql_agent_001",
    "endpoint_name": "heaap-sql-agent",
    "capabilities": ["generate_sql", "validate_sql"],
}

TESTS = [
    {
        "test_id": "EXT001",
        "capability": "generate_sql",
        "payload": {"question": "total annual premium"},
        "expected_status": "success",
    }
]


def make_review(status, authorized):
    verified = status == "approved" and authorized

    return {
        "agent": {
            "agent_id": MANIFEST["agent_id"],
            "endpoint_name": MANIFEST["endpoint_name"],
            "declared_capabilities": MANIFEST["capabilities"],
            "manifest_valid": True,
            "capabilities_verified": verified,
            "trust_status": (
                "verified" if verified else "unverified"
            ),
            "production_approved": False,
        },
        "discovered_endpoint": {
            "provider": "databricks",
            "endpoint_name": MANIFEST["endpoint_name"],
        },
        "review_status": status,
        "execution_authorized": authorized,
        "production_approved": False,
    }


def expect_blocked(review, label):
    try:
        validate_onboarding_approval(review, MANIFEST)
    except PermissionError:
        print(label, "PASS")
        return

    raise AssertionError(label + " unexpectedly allowed")


def main():
    print("HEAAP PHASE 19.1 - APPROVAL GATE TESTING")

    expect_blocked(
        make_review("pending_manual_review", False),
        "Pending review blocked:",
    )

    expect_blocked(
        make_review("rejected", False),
        "Rejected review blocked:",
    )

    expect_blocked(
        make_review("approved", False),
        "Missing authorization blocked:",
    )

    approved_review = make_review("approved", True)

    assert validate_onboarding_approval(
        approved_review, MANIFEST
    )

    print("Approved review validated: PASS")

    with patch(
        "app.services.external_agent_approval_gate."
        "load_onboarding_review",
        return_value=approved_review,
    ):
        report = run_approved_external_tests(
            "mock_review.json",
            MANIFEST,
            TESTS,
            approved_run=True,
        )

    assert report["passed_tests"] == 1
    assert report["failed_tests"] == 0
    assert report["governance"]["production_approved"] is False

    print("Approved mock test: PASS")
    print("Live endpoint invoked: False")
    print("PHASE 19.1: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
