import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.cross_agent_consistency_checker import (
    CrossAgentConsistencyChecker,
)


class DynamicMultiAgentTestOrchestrator:

    def __init__(
        self,
        *,
        agent_adapters,
        reference_provider,
        authorization_callback,
        output_dir=None,
    ):
        self.agent_adapters = agent_adapters
        self.reference_provider = reference_provider
        self.authorization_callback = authorization_callback

        self.checker = CrossAgentConsistencyChecker()

        self.output_dir = Path(
            output_dir or
            "reports/phase22_20/orchestration"
        )

    def run(
        self,
        test_cases,
        *,
        approved_run=False,
        execution_mode="simulated",
    ):
        if not approved_run:
            raise PermissionError(
                "Assurance run requires approval"
            )

        if execution_mode != "simulated":
            raise NotImplementedError(
                "Real-agent execution requires "
                "registry-backed authorization "
                "and verified execution adapters"
            )

        required_agents = [
            "metadata_agent",
            "sql_agent",
            "sql_validator_agent",
        ]

        for agent_id in required_agents:
            if agent_id not in self.agent_adapters:
                raise ValueError(
                    f"Missing adapter: {agent_id}"
                )

            if not self.authorization_callback(agent_id):
                raise PermissionError(
                    f"Agent not authorized: {agent_id}"
                )

        cycle_id = str(uuid.uuid4())
        results = []

        for test_case in test_cases:
            test_id = test_case["test_id"]
            question = test_case["question"]

            started = time.perf_counter()

            try:
                reference = self.reference_provider(
                    test_case
                )

                metadata = self.agent_adapters[
                    "metadata_agent"
                ](
                    question=question,
                    test_case=test_case,
                )

                sql_result = self.agent_adapters[
                    "sql_agent"
                ](
                    question=question,
                    metadata=metadata,
                    test_case=test_case,
                )

                validator_result = self.agent_adapters[
                    "sql_validator_agent"
                ](
                    sql=sql_result["sql"],
                    test_case=test_case,
                )

                consistency = self.checker.check(
                    question=question,
                    metadata_response=metadata,
                    sql_response=sql_result,
                    validator_response=validator_result,
                    trusted_reference=reference,
                )

                result = {
                    "test_id": test_id,
                    "question": question,
                    "status": consistency["status"],
                    "consistency_report": consistency,
                }

            except Exception as exc:
                result = {
                    "test_id": test_id,
                    "question": question,
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }

            result["duration_ms"] = round(
                (time.perf_counter() - started) * 1000,
                2,
            )

            results.append(result)

        summary = {
            "total": len(results),
            "consistent": sum(
                r["status"] == "consistent"
                for r in results
            ),
            "inconsistent": sum(
                r["status"] == "inconsistent"
                for r in results
            ),
            "inconclusive": sum(
                r["status"] == "inconclusive"
                for r in results
            ),
            "errors": sum(
                r["status"] == "error"
                for r in results
            ),
        }

        return {
            "cycle_id": cycle_id,
            "phase": "22.20",
            "execution_mode": execution_mode,
            "provenance_verified": False,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": summary,
            "results": results,
        }

    def save_report(self, report):
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        cycle_id = report["cycle_id"]
        uuid.UUID(cycle_id)

        path = self.output_dir / (
            f"assurance_cycle_{cycle_id}.json"
        )

        with path.open("x", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=2,
                default=str,
            )

        return str(path)
