"""
HEAAP Phase 22.6
Dynamic Agent Registration Service

Registers reviewed external agents using the existing
persistent registry and approval gate.

Discovery and classification do not grant approval.
"""

from pathlib import Path

from app.services.external_agent_approval_gate import (
    load_onboarding_review,
    validate_onboarding_approval,
)
from app.services.persistent_external_agent_registry import (
    PersistentExternalAgentRegistry,
)


class DynamicAgentRegistrationService:

    def __init__(self, registry=None):
        self.registry = (
            registry
            if registry is not None
            else PersistentExternalAgentRegistry()
        )

    def register_reviewed_agent(self, manifest, review_file):
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be an object")

        if not isinstance(manifest.get("agent_id"), str):
            raise ValueError("Missing agent_id")

        if not manifest["agent_id"].strip():
            raise ValueError("Empty agent_id")

        review_path = Path(review_file).resolve()

        # Read the approved review from the designated directory.
        review = load_onboarding_review(review_path)

        # Enforce all existing approval requirements.
        validate_onboarding_approval(review, manifest)

        # Registry independently repeats approval validation.
        agent_id = self.registry.register_agent(
            manifest,
            str(review_path),
        )

        return {
            "agent_id": agent_id,
            "registration_status": "registered",
            "approval_validated": True,
            "review_file": str(review_path),
        }

    def get_registered_agent(self, agent_id):
        # Existing registry revalidates approval on access.
        return self.registry.get_agent(agent_id)

    def list_registered_agents(self):
        return self.registry.list_agents()
