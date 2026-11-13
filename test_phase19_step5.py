"""HEAAP Phase 19.5 - Discovery to registry integration tests."""

import tempfile
from pathlib import Path

from app.services.external_agent_approval_gate import (
    load_onboarding_review,
)
from app.services.external_agent_discovery_registry_service import (
    ExternalAgentDiscoveryRegistryService,
)
from app.services.persistent_external_agent_registry import (
    PersistentExternalAgentRegistry,
)


REVIEW_FILE = (
    "reports/phase18_9_onboarding/"
    "ccccc93e0f114d618a46a865bc5dd76c.json"
)


def main():
    print("HEAAP PHASE 19.5 - DISCOVERY TO REGISTRY")
    print("=" * 55)

    review = load_onboarding_review(REVIEW_FILE)

    agent = review["agent"]

    manifest = {
        "agent_id": agent["agent_id"],
        "endpoint_name": agent["endpoint_name"],
        "capabilities": agent["declared_capabilities"],
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        registry = PersistentExternalAgentRegistry(
            Path(temp_dir) / "registry.db"
        )

        service = ExternalAgentDiscoveryRegistryService(
            registry=registry
        )

        candidate = service.inspect_candidate(
            manifest,
            review,
        )

        assert candidate["agent_id"] == (
            "external_sql_agent_001"
        )

        print("Existing external agent discovered: PASS")

        assert candidate["capabilities"] == [
            "generate_sql",
            "validate_sql",
        ]

        print("Declared capabilities inspected: PASS")

        assert candidate["review_status"] == (
            "pending_manual_review"
        )

        print("Pending review detected: PASS")

        assert candidate["registration_allowed"] is False

        print("Unapproved registration blocked: PASS")

        try:
            service.register_reviewed_candidate(
                manifest,
                REVIEW_FILE,
            )
        except PermissionError:
            print("Persistent registry protection: PASS")
        else:
            raise AssertionError(
                "Pending agent was registered"
            )

        assert service.list_registered_agents() == []

        print("Registry remains empty: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 19.5: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
