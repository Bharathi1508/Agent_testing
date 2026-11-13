"""HEAAP - Read-only unified registry dashboard."""

import json
from pathlib import Path

from app.services.persistent_external_agent_registry import (
    PersistentExternalAgentRegistry,
)


ROOT = Path(__file__).resolve().parents[2]

LOCAL_REGISTRY = ROOT / "app" / "registry" / "agent_registry.json"


class AgentRegistryDashboardService:

    def __init__(self, registry=None):
        self.registry = (
            registry
            if registry is not None
            else PersistentExternalAgentRegistry(
                db_path=ROOT / "reports" / "phase19_4" / "heaap_registry.db"
            )
        )

    def _local_agents(self):
        if not LOCAL_REGISTRY.is_file():
            return []

        with LOCAL_REGISTRY.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)

        records = data.get("agents", [])

        if not isinstance(records, list):
            raise ValueError("Local registry agents must be a list")

        agents = []

        for record in records:
            if not isinstance(record, dict):
                continue

            agent_id = record.get("agent_id")

            if not isinstance(agent_id, str) or not agent_id:
                continue

            capabilities = record.get("capabilities", [])

            if not isinstance(capabilities, list):
                capabilities = []

            agents.append({
                "agent_id": agent_id,
                "endpoint_name": record.get("endpoint"),
                "provider": record.get("runtime", "local"),
                "declared_capabilities": capabilities,
                "onboarding_status": "not_reviewed",
                "trust_status": "unverified",
                "production_approved": False,
            })

        return agents

    def _external_agents(self):
        agents = []

        for agent_id in self.registry.list_agents():

            # The persistent registry returns agent IDs.
            # Do not call get_agent() here because it enforces
            # onboarding approval and may raise for revoked reviews.

            if not isinstance(agent_id, str) or not agent_id:
                continue

            agents.append({
                "agent_id": agent_id,
                "endpoint_name": None,
                "provider": "external",
                "declared_capabilities": [],
                "onboarding_status": "requires_review_check",
                "trust_status": "unverified",
                "production_approved": False,
            })

        return agents

    def list_agents(self):
        combined = {}

        for agent in self._local_agents():
            combined[agent["agent_id"]] = agent

        for agent in self._external_agents():
            agent_id = agent["agent_id"]

            if agent_id in combined:
                # Do not silently merge conflicting registry identities.
                combined[agent_id]["trust_status"] = "registry_conflict"
                combined[agent_id]["onboarding_status"] = (
                    "manual_reconciliation_required"
                )
                combined[agent_id]["production_approved"] = False
            else:
                combined[agent_id] = agent

        return sorted(
            combined.values(),
            key=lambda item: item["agent_id"],
        )

    def get_summary(self):
        agents = self.list_agents()

        return {
            "total_agents": len(agents),
            "approved_agents": 0,
            "unapproved_agents": len(agents),
            "providers": sorted({
                agent["provider"]
                for agent in agents
            }),
        }
