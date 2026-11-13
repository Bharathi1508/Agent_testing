"""
HEAAP Phase 22.9 - Dynamic Test Execution Engine

Executes generated test cases against an explicitly
supplied local adapter and records execution evidence.

External agent execution is not implemented here.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class DynamicTestExecutionEngine:

    def __init__(self, output_dir="reports/phase22_9"):
        self.output_dir = Path(output_dir)

    def execute_tests(
        self,
        agent_id,
        tests,
        adapter,
        *,
        approved_run=False,
    ):
        if approved_run is not True:
            raise PermissionError(
                "Explicit test execution approval required"
            )

        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("Valid agent_id required")

        if not isinstance(tests, list):
            raise ValueError("Tests must be a list")

        if not callable(getattr(adapter, "execute", None)):
            raise TypeError("Adapter must implement execute()")

        results = []

        for test in tests:
            if not isinstance(test, dict):
                raise ValueError("Each test must be an object")

            if test.get("agent_id") != agent_id:
                raise PermissionError(
                    "Test agent identity mismatch"
                )

            test_id = test.get("test_id")

            if not isinstance(test_id, str) or not test_id:
                raise ValueError("Missing test_id")

            started_at = datetime.now(
                timezone.utc
            ).isoformat()

            try:
                actual_result = adapter.execute(test)
                execution_status = "completed"
                error = None
            except Exception as exc:
                actual_result = None
                execution_status = "error"
                error = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }

            results.append({
                "test_id": test_id,
                "agent_id": agent_id,
                "question": test.get("question"),
                "validation_method": test.get(
                    "validation_method"
                ),
                "expected_result": test.get(
                    "expected_result"
                ),
                "actual_result": actual_result,
                "execution_status": execution_status,
                "error": error,
                "started_at": started_at,
                "finished_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            })

        return {
            "run_id": str(uuid.uuid4()),
            "phase": "22.9",
            "agent_id": agent_id,
            "adapter_type": type(adapter).__name__,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total_tests": len(results),
            "completed": sum(
                r["execution_status"] == "completed"
                for r in results
            ),
            "errors": sum(
                r["execution_status"] == "error"
                for r in results
            ),
            "results": results,
        }

    def save_report(self, report):
        self.output_dir.mkdir(
            parents=True, exist_ok=True
        )

        run_id = report["run_id"]
        uuid.UUID(run_id)

        output_file = self.output_dir / (
            f"execution_{run_id}.json"
        )

        with output_file.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(output_file)
