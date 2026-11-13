"""
HEAAP Phase 22.7 - Dynamic Supervisor Service

Builds assurance plans for approved registered agents.
Does not invoke agents or execute test suites.
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import uuid

from app.services.agent_capability_classifier import (
    classify_agent,
)
from app.services.dynamic_agent_registration_service import (
    DynamicAgentRegistrationService,
)


class DynamicSupervisorService:

    def __init__(self, registration_service=None):
        self.registration_service = (
            registration_service
            if registration_service is not None
            else DynamicAgentRegistrationService()
        )

    def evaluate_agent(self, agent_id):
        """
        Build a test plan for one registered agent.

        get_registered_agent() revalidates onboarding approval.
        """

        try:
            record = self.registration_service.get_registered_agent(
                agent_id
            )

            manifest = record["manifest"]
            review = record["review"]

            classification = classify_agent(manifest)

            suites = classification["suggested_test_suites"]
            unmapped = classification["unmapped_capabilities"]

            if not suites or unmapped:
                return {
                    "agent_id": agent_id,
                    "status": "requires_review",
                    "suggested_test_suites": suites,
                    "unmapped_capabilities": unmapped,
                    "tests_executed": 0,
                    "reason": "Missing or unmapped test capabilities",
                }

            return {
                "agent_id": agent_id,
                "status": "ready_for_testing",
                "framework": manifest.get("framework"),
                "declared_capabilities": manifest.get(
                    "capabilities", []
                ),
                "suggested_test_suites": suites,
                "unmapped_capabilities": [],
                "onboarding_review_status": review.get(
                    "review_status"
                ),
                "tests_executed": 0,
                "reason": "Approved agent; execution not started",
            }

        except (
            LookupError,
            PermissionError,
            FileNotFoundError,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            return {
                "agent_id": agent_id,
                "status": "blocked",
                "tests_executed": 0,
                "reason": f"{type(error).__name__}: {error}",
            }

    def evaluate_all_agents(self):
        """
        Build plans for every registered agent.
        """

        agent_ids = self.registration_service.list_registered_agents()

        results = []

        for agent_id in agent_ids:
            results.append(self.evaluate_agent(agent_id))

        summary = {
            "total_agents": len(results),
            "ready_for_testing": sum(
                r["status"] == "ready_for_testing"
                for r in results
            ),
            "requires_review": sum(
                r["status"] == "requires_review"
                for r in results
            ),
            "blocked": sum(
                r["status"] == "blocked"
                for r in results
            ),
            "tests_executed": 0,
        }

        return {
            "run_id": str(uuid.uuid4()),
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "phase": "22.7",
            "report_type": "supervisor_test_plan",
            "summary": summary,
            "agents": results,
        }

    def save_report(self, report):
        directory = Path("reports/phase22_7")
        directory.mkdir(parents=True, exist_ok=True)

        run_id = report["run_id"]
        uuid.UUID(run_id)

        output_file = directory / f"supervisor_{run_id}.json"

        with output_file.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(output_file)

class SupervisorAuthorizationError(Exception):
    pass


class SupervisorExecutionError(Exception):
    pass

def execute_supervisor_request(
    *,
    capability,
    payload,
    preferred_agent_id=None,
):
    """
    Resolve an approved active agent and execute it.

    This does not approve or activate agents.
    """

    from app.services.dynamic_router import (
        resolve_agent,
        AgentNotApprovedError,
        AgentNotFoundError,
        MultipleAgentsFoundError,
    )

    from app.services.agent_executor import (
        execute_agent,
        AgentExecutionError,
    )

    if not isinstance(payload, dict):
        raise SupervisorExecutionError(
            "Agent payload must be a dictionary."
        )

    try:
        selected_agent = resolve_agent(
            capability=capability,
            preferred_agent_id=preferred_agent_id,
        )

    except (
        AgentNotApprovedError,
        AgentNotFoundError,
    ) as exc:
        raise SupervisorAuthorizationError(
            str(exc)
        ) from exc

    except MultipleAgentsFoundError as exc:
        raise SupervisorExecutionError(
            str(exc)
        ) from exc

    try:
        result = execute_agent(
            manifest=selected_agent,
            payload=payload,
        )

    except AgentExecutionError as exc:
        raise SupervisorExecutionError(
            str(exc)
        ) from exc

    return {
        "agent_id": selected_agent.agent_id,
        "capability": capability,
        "execution_type": selected_agent.execution_type,
        "status": "completed",
        "result": result,
    }
