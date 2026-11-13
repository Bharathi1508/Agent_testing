"""
HEAAP Phase 22.18
Automated Agent Readiness Service.

Read-only registry inspection.
No registration, approval, or agent execution.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.persistent_external_agent_registry import (
    PersistentExternalAgentRegistry,
)


CAPABILITY_SUITES = {
    "metadata_search": "metadata_correctness",
    "schema_discovery": "schema_validation",
    "column_description": "column_description_validation",
    "sql_generation": "sql_generation_validation",
    "sql_validation": "sql_safety_validation",
    "sql_execution": "sql_execution_validation",
    "fraud_detection": "fraud_detection_evaluation",
}


class AutomatedAgentReadinessService:

    def __init__(self, registry=None):
        self.registry = (
            registry
            if registry is not None
            else PersistentExternalAgentRegistry()
        )

    def inspect_agent(self, agent_id):
        try:
            record = self.registry.get_agent(agent_id)

            manifest = record["manifest"]
            review = record["review"]

            if manifest.get("agent_id") != agent_id:
                raise ValueError("Agent identity mismatch")

            if (
                review.get("agent", {}).get("agent_id")
                != agent_id
            ):
                raise ValueError("Review identity mismatch")

            capabilities = manifest.get(
                "capabilities", []
            )

            if not isinstance(capabilities, list):
                raise ValueError("Invalid capabilities")

            suites = sorted({
                CAPABILITY_SUITES[capability]
                for capability in capabilities
                if capability in CAPABILITY_SUITES
            })

            unsupported = sorted({
                capability
                for capability in capabilities
                if capability not in CAPABILITY_SUITES
            })

            return {
                "agent_id": agent_id,
                "status": (
                    "ready_for_test_planning"
                    if suites
                    else "unsupported_capabilities"
                ),
                "capabilities": capabilities,
                "suggested_test_suites": suites,
                "unsupported_capabilities": unsupported,
                "tests_executed": 0,
            }

        except Exception as exc:
            return {
                "agent_id": agent_id,
                "status": "blocked",
                "reason": type(exc).__name__,
                "tests_executed": 0,
            }

    def run(self):
        agent_ids = self.registry.list_agents()

        agents = [
            self.inspect_agent(agent_id)
            for agent_id in agent_ids
        ]

        return {
            "report_id": str(uuid.uuid4()),
            "phase": "22.18",
            "report_type": "readiness_only",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": {
                "total_registered": len(agents),
                "ready_for_test_planning": sum(
                    a["status"] == "ready_for_test_planning"
                    for a in agents
                ),
                "unsupported": sum(
                    a["status"] == "unsupported_capabilities"
                    for a in agents
                ),
                "blocked": sum(
                    a["status"] == "blocked"
                    for a in agents
                ),
                "tests_executed": 0,
            },
            "agents": agents,
        }

    def save_report(
        self,
        report,
        output_dir="reports/phase22_18",
    ):
        folder = Path(output_dir)
        folder.mkdir(parents=True, exist_ok=True)

        report_id = report["report_id"]
        uuid.UUID(report_id)

        path = folder / f"readiness_{report_id}.json"

        with path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(path)
