"""
HEAAP Phase 22.19 - Step 9
Unified Assurance Reporting Service.

Combines:
- Multi-agent execution summary
- Individual test evidence, when available
- Failure classification

Does not execute agents or grant approvals.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.agent_failure_analysis_engine import (
    AgentFailureAnalysisEngine,
)


class UnifiedAssuranceReportingService:

    def __init__(self, failure_engine=None):
        self.failure_engine = (
            failure_engine
            if failure_engine is not None
            else AgentFailureAnalysisEngine()
        )

    def generate(
        self,
        execution_report,
        test_results=None,
        *,
        evidence_type="unverified",
    ):
        if not isinstance(execution_report, dict):
            raise ValueError(
                "Execution report must be a dictionary"
            )

        if not isinstance(
            execution_report.get("summary"), dict
        ):
            raise ValueError(
                "Execution report summary is missing"
            )

        if not isinstance(
            execution_report.get("agents"), list
        ):
            raise ValueError(
                "Execution report agents are missing"
            )

        if test_results is None:
            test_results = []

        if not isinstance(test_results, list):
            raise ValueError(
                "Test results must be a list"
            )

        if evidence_type not in (
            "simulated",
            "verified_real_execution",
            "unverified",
        ):
            raise ValueError(
                "Invalid evidence type"
            )

        # Only the caller can supply the provenance label.
        # This service does not independently verify it.
        analysis_inputs = list(test_results)

        # Add coordinator-level blocked/error events.
        # Do not treat these as individual test failures.
        for agent in execution_report["agents"]:
            status = agent.get("status")

            if status not in ("blocked", "error"):
                continue

            analysis_inputs.append({
                "agent_id": agent.get("agent_id"),
                "test_id": None,
                "status": (
                    "blocked"
                    if status == "blocked"
                    else "error"
                ),
                "reason": agent.get("reason"),
            })

        failure_analysis = self.failure_engine.analyze(
            analysis_inputs
        )

        return {
            "unified_report_id": str(uuid.uuid4()),
            "phase": "22.19-step9",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "source_cycle_id": execution_report.get(
                "cycle_id"
            ),
            "evidence_type": evidence_type,
            "provenance_verified_by_service": False,
            "execution_summary": execution_report["summary"],
            "agents": execution_report["agents"],
            "failure_analysis": failure_analysis,
            "test_evidence_count": len(test_results),
            "limitations": [
                "Individual failures require detailed evaluator results.",
                "Agent-level errors are not counted as completed test failures.",
                "Evidence provenance requires independent verification.",
            ],
        }

    def save_report(
        self,
        report,
        output_dir="reports/phase22_19/unified",
    ):
        folder = Path(output_dir)
        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        report_id = report["unified_report_id"]
        uuid.UUID(report_id)

        path = folder / (
            f"unified_assurance_{report_id}.json"
        )

        with path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(path)
