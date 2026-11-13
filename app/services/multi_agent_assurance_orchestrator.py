"""
HEAAP Phase 22.12A
Automated Multi-Agent Assurance Orchestrator

Coordinates safe assurance planning for all registered
agents.

This module does not invoke external agents,
execute tests, or grant onboarding approval.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.dynamic_supervisor_service import (
    DynamicSupervisorService,
)


class MultiAgentAssuranceOrchestrator:

    def __init__(
        self,
        supervisor=None,
        output_dir="reports/phase22_12",
    ):
        self.supervisor = (
            supervisor
            if supervisor is not None
            else DynamicSupervisorService()
        )
        self.output_dir = Path(output_dir)

    def run_planning_cycle(self):
        """
        Build a consolidated assurance plan.

        The supervisor revalidates registered agents
        through the existing registry approval checks.
        """

        supervisor_report = (
            self.supervisor.evaluate_all_agents()
        )

        agents = supervisor_report.get("agents", [])

        if not isinstance(agents, list):
            raise ValueError("Invalid supervisor report")

        planned_agents = []

        for agent in agents:
            status = agent.get("status")

            planned_agents.append({
                "agent_id": agent.get("agent_id"),
                "eligibility_status": status,
                "suggested_test_suites": agent.get(
                    "suggested_test_suites", []
                ),
                "reason": agent.get("reason"),
                "execution_status": "not_started",
                "tests_executed": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "tests_errored": 0,
            })

        return {
            "cycle_id": str(uuid.uuid4()),
            "phase": "22.12A",
            "cycle_type": "planning_only",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": {
                "total_agents": len(planned_agents),
                "ready_for_testing": sum(
                    a["eligibility_status"]
                    == "ready_for_testing"
                    for a in planned_agents
                ),
                "requires_review": sum(
                    a["eligibility_status"]
                    == "requires_review"
                    for a in planned_agents
                ),
                "blocked": sum(
                    a["eligibility_status"] == "blocked"
                    for a in planned_agents
                ),
                "tests_executed": 0,
            },
            "agents": planned_agents,
        }

    def save_report(self, report):
        self.output_dir.mkdir(
            parents=True, exist_ok=True
        )

        cycle_id = report["cycle_id"]
        uuid.UUID(cycle_id)

        path = self.output_dir / (
            f"assurance_cycle_{cycle_id}.json"
        )

        with path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(path)
