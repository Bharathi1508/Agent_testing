"""
HEAAP Phase 22.10
Agent Result Evaluator.

Evaluates metadata test execution results.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class AgentResultEvaluator:

    def evaluate(self, execution_report):

        if not isinstance(execution_report, dict):
            raise ValueError("Invalid execution report")

        results = execution_report.get("results")

        if not isinstance(results, list):
            raise ValueError("Missing execution results")

        evaluated = []
        passed = 0
        failed = 0
        errors = 0

        for item in results:

            if not isinstance(item, dict):
                raise ValueError("Invalid test result")

            expected = item.get("expected")
            actual = item.get("actual")
            test_type = item.get("test_type")

            if item.get("error") is not None:
                status = "error"

            elif test_type == "exact_boolean":
                if (
                    isinstance(expected, dict)
                    and isinstance(actual, dict)
                    and type(expected.get("exists")) is bool
                    and type(actual.get("exists")) is bool
                ):
                    status = (
                        "passed"
                        if expected["exists"] == actual["exists"]
                        else "failed"
                    )
                else:
                    status = "error"

            elif test_type == "exact_type":
                if (
                    isinstance(expected, dict)
                    and isinstance(actual, dict)
                    and isinstance(expected.get("data_type"), str)
                    and isinstance(actual.get("data_type"), str)
                ):
                    status = (
                        "passed"
                        if expected["data_type"].strip().lower()
                        == actual["data_type"].strip().lower()
                        else "failed"
                    )
                else:
                    status = "error"

            else:
                status = "error"

            if status == "passed":
                passed += 1
            elif status == "failed":
                failed += 1
            else:
                errors += 1

            evaluated.append({
                **item,
                "evaluation_status": status,
            })

        total = len(evaluated)

        return {
            "evaluation_id": str(uuid.uuid4()),
            "agent_id": execution_report.get("agent_id"),
            "evaluated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "overall_pass_rate_pct": round(
                    passed / total * 100, 2
                ) if total else 0,
                "completed_accuracy_pct": round(
                    passed / (passed + failed) * 100, 2
                ) if (passed + failed) else 0,
            },
            "results": evaluated,
        }

    def save_report(
        self,
        report,
        output_dir="reports/phase22_10",
    ):
        folder = Path(output_dir)
        folder.mkdir(parents=True, exist_ok=True)

        evaluation_id = report["evaluation_id"]
        uuid.UUID(evaluation_id)

        path = folder / f"evaluation_{evaluation_id}.json"

        with path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(path)
