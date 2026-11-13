"""HEAAP Phase 19.2 - Dynamic routing tests."""

from app.services.external_agent_router import (
    ExternalAgentRouter,
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


def main():
    print("HEAAP PHASE 19.2 - DYNAMIC AGENT ROUTING")
    print("=" * 50)

    router = ExternalAgentRouter()

    agents = [
        make_agent(
            "external_sql_agent_001",
            "heaap-sql-agent",
            ["generate_sql", "validate_sql"],
        ),
        make_agent(
            "external_metadata_agent_001",
            "heaap-metadata-agent",
            ["get_metadata"],
        ),
        make_agent(
            "external_fraud_agent_001",
            "heaap-fraud-agent",
            ["detect_fraud"],
        ),
    ]

    for manifest, review in agents:
        router.register_agent(manifest, review)

    expected_routes = {
        "generate_sql": "external_sql_agent_001",
        "validate_sql": "external_sql_agent_001",
        "get_metadata": "external_metadata_agent_001",
        "detect_fraud": "external_fraud_agent_001",
    }

    for capability, expected_agent in expected_routes.items():
        result = router.route(capability)

        assert result["agent_id"] == expected_agent
        assert result["endpoint_invoked"] is False

        print(capability, "->", result["agent_id"], "PASS")

    pending_manifest, pending_review = make_agent(
        "unapproved_agent_001",
        "unapproved-endpoint",
        ["generate_sql"],
        approved=False,
    )

    try:
        router.register_agent(
            pending_manifest,
            pending_review,
        )
    except PermissionError:
        print("Unapproved agent blocked: PASS")
    else:
        raise AssertionError("Unapproved agent was registered")

    try:
        router.route("delete_database")
    except LookupError:
        print("Unknown capability blocked: PASS")
    else:
        raise AssertionError("Unknown capability was routed")

    print()
    print("Registered agents:", len(router.agents))
    print("Live endpoint invoked: False")
    print("PHASE 19.2: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
