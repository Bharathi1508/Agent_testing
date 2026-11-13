"""HEAAP Phase 19.2 - Dynamic external agent routing."""

from app.services.external_agent_approval_gate import (
    validate_onboarding_approval,
)


class ExternalAgentRouter:

    def __init__(self):
        self.agents = {}

    def register_agent(self, manifest, review):
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be a dictionary")

        agent_id = manifest.get("agent_id")
        capabilities = manifest.get("capabilities")

        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("Invalid agent ID")

        if (
            not isinstance(capabilities, list)
            or not capabilities
            or not all(isinstance(c, str) and c for c in capabilities)
            or len(capabilities) != len(set(capabilities))
        ):
            raise ValueError("Invalid capabilities")

        if agent_id in self.agents:
            raise ValueError("Agent already registered")

        validate_onboarding_approval(review, manifest)

        self.agents[agent_id] = {
            "manifest": manifest.copy(),
            "review": review.copy(),
        }

        return agent_id

    def find_agents_by_capability(self, capability):
        matches = []

        for agent_id, record in self.agents.items():
            if capability in record["manifest"]["capabilities"]:
                matches.append(agent_id)

        return sorted(matches)

    def route(self, capability, agent_id=None):
        if not isinstance(capability, str) or not capability:
            raise ValueError("Invalid capability")

        candidates = self.find_agents_by_capability(capability)

        if agent_id is not None:
            if agent_id not in candidates:
                raise LookupError(
                    "Requested agent does not support capability"
                )
            selected_id = agent_id
        else:
            if not candidates:
                raise LookupError("No approved agent found")

            if len(candidates) > 1:
                raise LookupError(
                    "Multiple approved agents found; "
                    "specify agent_id"
                )

            selected_id = candidates[0]

        record = self.agents[selected_id]

        # Revalidate before returning the route.
        validate_onboarding_approval(
            record["review"],
            record["manifest"],
        )

        return {
            "agent_id": selected_id,
            "capability": capability,
            "endpoint_name": record["manifest"]["endpoint_name"],
            "adapter_type": "databricks_mock",
            "endpoint_invoked": False,
        }
