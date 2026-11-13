"""HEAAP Phase 20.0 - Dynamic multi-agent assurance coordinator."""

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.dynamic_external_test_planner import (
    generate_dynamic_test_plan,
)
from app.services.phase19_langgraph_supervisor import (
    run_langgraph_supervisor,
)


class DynamicMultiAgentAssuranceCoordinator:

    def __init__(self, mock_executor=None):
        self.mock_executor = mock_executor

    def evaluate_agent(self, manifest, review):
        if not isinstance(manifest, dict):
            raise ValueError("Invalid manifest")

        if not isinstance(review, dict):
            raise ValueError("Invalid review")

        agent_id = manifest.get("agent_id")

        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("Missing agent ID")

        plan = generate_dynamic_test_plan(manifest)

        plan["source_review_id"] = review.get("review_id")
        plan["source_review_status"] = review.get(
            "review_status"
        )

        supervisor = run_langgraph_supervisor(
            plan,
            review,
        )

        decision = supervisor["supervisor_decision"]
        validation = supervisor["plan_validation"]

        result = {
            "agent_id": agent_id,
            "plan_id": plan["plan_id"],
            "capabilities": manifest["capabilities"],
            "total_planned_tests": plan["total_tests"],
            "unsupported_capabilities": plan[
                "unsupported_capabilities"
            ],
            "plan_valid": validation["valid"],
            "supervisor_decision": decision["decision"],
            "tests_executed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "verdict": "BLOCKED",
            "test_results": [],
        }

        # Phase 20.0 deliberately does not execute tests.
        # Even an approved review is not a run authorization.
        if (
            decision["decision"] == "ready_for_run_approval"
            and not plan["unsupported_capabilities"]
            and plan["total_tests"] > 0
        ):
            result["verdict"] = "READY_FOR_RUN_APPROVAL"

        return result

    def evaluate_agents(self, agents):
        if not isinstance(agents, list):
            raise ValueError("Agents must be a list")

        results = []
        seen_ids = set()

        for item in agents:
            if not isinstance(item, dict):
                raise ValueError("Invalid agent entry")

            manifest = item.get("manifest")
            review = item.get("review")

            if not isinstance(manifest, dict):
                raise ValueError("Missing manifest")

            agent_id = manifest.get("agent_id")

            if agent_id in seen_ids:
                raise ValueError("Duplicate agent ID")

            seen_ids.add(agent_id)

            results.append(
                self.evaluate_agent(manifest, review)
            )

        ready = sum(
            r["verdict"] == "READY_FOR_RUN_APPROVAL"
            for r in results
        )

        blocked = sum(
            r["verdict"] == "BLOCKED"
            for r in results
        )

        return {
            "report_id": uuid.uuid4().hex,
            "phase": "20.0",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total_agents": len(results),
            "ready_for_run_approval": ready,
            "blocked_agents": blocked,
            "agents": results,
            "governance": {
                "execution_authorized": False,
                "live_endpoint_invoked": False,
                "production_approved": False,
            },
        }


def save_multi_agent_report(report, output_dir=None):
    if output_dir is None:
        output_dir = Path("reports/phase20_0")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / (
        report["report_id"] + ".json"
    )

    with output_file.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    return str(output_file)
