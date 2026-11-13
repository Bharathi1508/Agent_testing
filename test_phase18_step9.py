"""Phase 18.9 - External discovery and onboarding tests."""

from app.services.external_agent_discovery import (
    discover_databricks_endpoints,
)
from app.services.external_agent_manifest_validator import (
    validate_external_manifest,
)
from app.services.external_agent_onboarding import (
    prepare_external_onboarding,
    save_onboarding_review,
)


FIXTURE = {
    "endpoints": [
        {
            "name": "he aap-sql-agent".replace(" ", ""),
            "state": {"ready": "READY"},
        },
        {
            "name": "he aap-fraud-agent".replace(" ", ""),
            "state": {"ready": "READY"},
        },
    ]
}

MANIFEST = {
    "agent_id": "external_sql_agent_001",
    "name": "External SQL Agent",
    "framework": "databricks",
    "execution_type": "external",
    "endpoint_name": "heaap-sql-agent",
    "capabilities": [
        "generate_sql",
        "validate_sql",
    ],
}


def expect_value_error(action):
    try:
        action()
    except ValueError:
        return

    raise AssertionError("Expected ValueError")


def main():
    print("=" * 55)
    print("HEAAP PHASE 18.9 - EXTERNAL AGENT ONBOARDING")
    print("=" * 55)

    discovery = discover_databricks_endpoints(
        live=False,
        fixture=FIXTURE,
    )

    assert discovery["candidate_count"] == 2
    assert discovery["live_discovery"] is False

    print("PASS: Endpoint inventory discovered")

    validated = validate_external_manifest(MANIFEST)

    assert validated["manifest_valid"] is True
    assert validated["capabilities_verified"] is False

    print("PASS: External manifest validated")

    review = prepare_external_onboarding(
        MANIFEST,
        discovery,
    )

    assert review["review_status"] == (
        "pending_manual_review"
    )
    assert review["execution_authorized"] is False
    assert review["automatically_registered"] is False

    print("PASS: Onboarding review prepared")

    path = save_onboarding_review(review)

    print("PASS: Onboarding review saved")

    invalid = dict(MANIFEST)
    invalid["capabilities"] = []

    expect_value_error(
        lambda: validate_external_manifest(invalid)
    )

    print("PASS: Invalid capabilities rejected")

    unknown = dict(MANIFEST)
    unknown["endpoint_name"] = "unknown-endpoint"

    expect_value_error(
        lambda: prepare_external_onboarding(
            unknown, discovery
        )
    )

    print("PASS: Unknown endpoint rejected")

    assert review["production_approved"] is False

    print("PASS: Production approval remains disabled")

    print()
    print("Discovered endpoints:",
          discovery["candidate_count"])
    print("Agent:", validated["agent_id"])
    print("Capabilities:",
          validated["declared_capabilities"])
    print("Review status:", review["review_status"])
    print("Review file:", path)
    print("Execution authorized:",
          review["execution_authorized"])
    print()
    print("PHASE 18.9: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
