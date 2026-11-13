"""HEAAP Phase 19.5 - Discovery to persistent registry integration."""

from app.services.external_agent_approval_gate import (
    validate_onboarding_approval,
)
from app.services.persistent_external_agent_registry import (
    PersistentExternalAgentRegistry,
)


class ExternalAgentDiscoveryRegistryService:
    def __init__(self, registry=None):
        self.registry = (
            registry if registry is not None
            else PersistentExternalAgentRegistry()
        )

    def inspect_candidate(self, manifest, review):
        """Inspect a discovered candidate without registering it."""

        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be an object")

        if not isinstance(review, dict):
            raise ValueError("Review must be an object")

        agent_id = manifest.get("agent_id")

        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("Missing agent ID")

        reviewed_agent = review.get("agent")

        if not isinstance(reviewed_agent, dict):
            raise ValueError("Missing reviewed agent")

        if reviewed_agent.get("agent_id") != agent_id:
            raise PermissionError("Agent identity mismatch")

        if (
            reviewed_agent.get("endpoint_name")
            != manifest.get("endpoint_name")
        ):
            raise PermissionError("Endpoint mismatch")

        if reviewed_agent.get("manifest_valid") is not True:
            raise PermissionError("Invalid manifest")

        capabilities = manifest.get("capabilities")

        if (
            not isinstance(capabilities, list)
            or not capabilities
            or not all(
                isinstance(item, str) and item
                for item in capabilities
            )
            or len(capabilities) != len(set(capabilities))
        ):
            raise ValueError("Invalid capabilities")

        declared = reviewed_agent.get("declared_capabilities")

        if (
            not isinstance(declared, list)
            or set(declared) != set(capabilities)
            or len(declared) != len(capabilities)
        ):
            raise PermissionError("Capability mismatch")

        return {
            "agent_id": agent_id,
            "endpoint_name": manifest["endpoint_name"],
            "capabilities": capabilities,
            "review_status": review.get("review_status"),
            "registration_allowed": (
                review.get("review_status") == "approved"
                and review.get("execution_authorized") is True
                and reviewed_agent.get("capabilities_verified") is True
                and reviewed_agent.get("trust_status") == "verified"
            ),
            "automatically_registered": False,
            "live_endpoint_invoked": False,
        }

    def register_reviewed_candidate(self, manifest, review_file):
        """Register only after current review validation."""

        from app.services.external_agent_approval_gate import (
            load_onboarding_review,
        )

        review = load_onboarding_review(review_file)

        validate_onboarding_approval(review, manifest)

        return self.registry.register_agent(
            manifest,
            review_file,
        )

    def list_registered_agents(self):
        return self.registry.list_agents()
