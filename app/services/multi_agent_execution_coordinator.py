import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.automated_agent_readiness_service import (
    AutomatedAgentReadinessService,
)


class MultiAgentExecutionCoordinator:

    def __init__(
        self,
        readiness_service=None,
        runner_factory=None,
        authorization_check=None,
    ):
        self.readiness_service = (
            readiness_service
            if readiness_service is not None
            else AutomatedAgentReadinessService()
        )
        self.runner_factory = runner_factory
        self.authorization_check = authorization_check

    def run(self, agent_configs, *, approved_run=False):

        if approved_run is not True:
            raise PermissionError(
                "Explicit execution approval required"
            )

        if not callable(self.authorization_check):
            raise PermissionError(
                "Governance authorization required"
            )

        if not callable(self.runner_factory):
            raise ValueError("Runner factory required")

        if not isinstance(agent_configs, dict):
            raise ValueError("Invalid agent configurations")

        readiness = self.readiness_service.run()
        results = []

        for agent in readiness["agents"]:
            agent_id = agent["agent_id"]

            result = {
                "agent_id": agent_id,
                "status": "skipped",
                "reason": None,
                "summary": None,
            }

            if agent.get("status") != "ready_for_test_planning":
                result["reason"] = "Agent not ready"
                results.append(result)
                continue

            try:
                if self.authorization_check(agent_id) is not True:
                    raise PermissionError(
                        "Agent not authorized"
                    )

                config = agent_configs.get(agent_id)

                if not isinstance(config, dict):
                    result["reason"] = "Missing configuration"
                    results.append(result)
                    continue

                tests = config.get("tests")
                adapter = config.get("adapter")

                if not isinstance(tests, list) or not tests:
                    result["reason"] = "No tests provided"
                    results.append(result)
                    continue

                if adapter is None:
                    result["reason"] = "No adapter provided"
                    results.append(result)
                    continue

                if config.get("reference_verified") is not True:
                    result["reason"] = "Reference not verified"
                    results.append(result)
                    continue

                runner = self.runner_factory(agent_id)

                report = runner.run(
                    agent_id=agent_id,
                    tests=tests,
                    adapter=adapter,
                    approved_run=True,
                    reference_verified=True,
                )

                evaluation = report["evaluation_report"]

                result["status"] = "completed"
                result["summary"] = evaluation["summary"]
                result["evaluation_id"] = evaluation.get(
                    "evaluation_id"
                )

            except PermissionError:
                result["status"] = "blocked"
                result["reason"] = "Authorization failed"

            except Exception as exc:
                result["status"] = "error"
                result["reason"] = (
                    f"{type(exc).__name__}: {exc}"
                )

            results.append(result)

        completed = [
            item for item in results
            if item["status"] == "completed"
        ]

        def total(field):
            return sum(
                item["summary"].get(field, 0)
                for item in completed
            )

        total_tests = total("total_tests")
        passed = total("passed")

        return {
            "cycle_id": str(uuid.uuid4()),
            "phase": "22.19",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": {
                "total_agents": len(results),
                "completed_agents": len(completed),
                "blocked_agents": sum(
                    item["status"] == "blocked"
                    for item in results
                ),
                "skipped_agents": sum(
                    item["status"] == "skipped"
                    for item in results
                ),
                "errored_agents": sum(
                    item["status"] == "error"
                    for item in results
                ),
                "total_tests": total_tests,
                "passed": passed,
                "failed": total("failed"),
                "errors": total("errors"),
                "overall_pass_rate_pct": round(
                    passed / total_tests * 100, 2
                ) if total_tests else 0,
            },
            "agents": results,
        }

    def save_report(
        self,
        report,
        output_dir="reports/phase22_19",
    ):
        folder = Path(output_dir)
        folder.mkdir(parents=True, exist_ok=True)

        cycle_id = report["cycle_id"]
        uuid.UUID(cycle_id)

        path = folder / (
            f"multi_agent_assurance_{cycle_id}.json"
        )

        with path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(path)
