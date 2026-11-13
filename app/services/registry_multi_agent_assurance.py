"""HEAAP Phase 20.1 - Registry-driven multi-agent assurance."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.dynamic_multi_agent_assurance import (
    DynamicMultiAgentAssuranceCoordinator,
)
from app.services.external_agent_approval_gate import (
    load_onboarding_review,
)


class RegistryMultiAgentAssuranceService:
    def __init__(self, registry, review_loader=None):
        self.registry = registry
        self.review_loader = (
            review_loader
            if review_loader is not None
            else load_onboarding_review
        )
        self.coordinator = DynamicMultiAgentAssuranceCoordinator()

    def _read_registry_record(self, agent_id):
        record = self.registry.get_agent(agent_id)

        if not isinstance(record, dict):
            raise ValueError("Missing or invalid registry record")

        # Support both common registry response formats:
        # {"manifest": {...}, "review_file": "..."}
        # {"manifest": {...}, "review": {...}}
        manifest = record.get("manifest")

        if manifest is None:
            manifest = record.get("agent_manifest")

        if not isinstance(manifest, dict):
            raise ValueError("Registry manifest is missing")

        if manifest.get("agent_id") != agent_id:
            raise PermissionError("Registry agent identity mismatch")

        review_file = record.get("review_file")

        if not isinstance(review_file, (str, Path)):
            raise ValueError("Registry review file is missing")

        # Reload the current review rather than trusting a
        # review object returned from the registry.
        review = self.review_loader(str(review_file))

        if not isinstance(review, dict):
            raise ValueError("Invalid onboarding review")

        reviewed_agent = review.get("agent")

        if not isinstance(reviewed_agent, dict):
            raise ValueError("Missing reviewed agent")

        if reviewed_agent.get("agent_id") != agent_id:
            raise PermissionError("Review identity mismatch")

        if (
            reviewed_agent.get("endpoint_name")
            != manifest.get("endpoint_name")
        ):
            raise PermissionError("Endpoint identity mismatch")

        if (
            reviewed_agent.get("declared_capabilities")
            != manifest.get("capabilities")
        ):
            raise PermissionError("Capability identity mismatch")

        return {
            "manifest": manifest,
            "review": review,
        }

    def evaluate_registered_agents(self):
        agent_ids = self.registry.list_agents()

        if not isinstance(agent_ids, list):
            raise ValueError("Registry must return a list")

        if len(agent_ids) != len(set(agent_ids)):
            raise ValueError("Duplicate registered agent IDs")

        results = []

        for agent_id in agent_ids:
            if not isinstance(agent_id, str) or not agent_id:
                raise ValueError("Invalid registered agent ID")

            try:
                entry = self._read_registry_record(agent_id)

                result = self.coordinator.evaluate_agent(
                    entry["manifest"],
                    entry["review"],
                )

                # Unsupported capabilities cannot be cleared
                # for a run even if onboarding is approved.
                if result["unsupported_capabilities"]:
                    result["verdict"] = "BLOCKED"

                results.append(result)

            except Exception as exc:
                # Fail closed for individual agents while
                # continuing the registry-wide assessment.
                results.append({
                    "agent_id": agent_id,
                    "verdict": "BLOCKED",
                    "reason": str(exc),
                    "error_type": type(exc).__name__,
                    "tests_executed": 0,
                    "tests_passed": 0,
                    "tests_failed": 0,
                })

        ready = sum(
            item["verdict"] == "READY_FOR_RUN_APPROVAL"
            for item in results
        )

        blocked = sum(
            item["verdict"] == "BLOCKED"
            for item in results
        )

        return {
            "report_id": uuid.uuid4().hex,
            "phase": "20.1",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "discovered_registered_agents": len(agent_ids),
            "ready_for_run_approval": ready,
            "blocked_agents": blocked,
            "agents": results,
            "governance": {
                "execution_authorized": False,
                "live_endpoint_invoked": False,
                "production_approved": False,
            },
        }


def save_registry_assurance_report(report, output_dir=None):
    if output_dir is None:
        output_dir = Path("reports/phase20_1")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / (
        report["report_id"] + ".json"
    )

    with report_path.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    return str(report_path)
