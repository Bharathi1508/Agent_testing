import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class AssuranceScoringEngine:

    SEVERITY_WEIGHTS = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 5,
    }

    VALID_STATUSES = {
        "consistent",
        "inconsistent",
        "inconclusive",
        "error",
    }

    def __init__(self, output_dir=None):
        self.output_dir = Path(
            output_dir or "reports/phase22_20/scoring"
        )

    def score(self, orchestration_report):
        results = orchestration_report.get("results", [])

        if not results:
            raise ValueError(
                "Cannot score an empty assurance cycle"
            )

        total_weight = 0
        passed_weight = 0

        summary = {
            "total": len(results),
            "consistent": 0,
            "inconsistent": 0,
            "inconclusive": 0,
            "errors": 0,
        }

        findings = []

        for result in results:
            test_id = result.get("test_id")
            status = result.get("status", "error")
            severity = result.get("severity", "medium")

            if status not in self.VALID_STATUSES:
                raise ValueError(
                    f"Unknown test status: {status}"
                )

            if severity not in self.SEVERITY_WEIGHTS:
                raise ValueError(
                    f"Unknown severity: {severity}"
                )

            weight = self.SEVERITY_WEIGHTS[severity]
            total_weight += weight

            if status == "consistent":
                passed_weight += weight

            if status == "error":
                summary["errors"] += 1
            else:
                summary[status] += 1

            if status != "consistent":
                findings.append({
                    "test_id": test_id,
                    "status": status,
                    "severity": severity,
                    "weight": weight,
                })

        score = round(
            (passed_weight / total_weight) * 100,
            2,
        )

        unresolved = (
            summary["inconclusive"] +
            summary["errors"]
        )

        if unresolved > 0:
            readiness = "manual_review"
        elif score >= 95:
            readiness = "candidate_for_approval"
        elif score >= 80:
            readiness = "needs_improvement"
        else:
            readiness = "high_risk"

        return {
            "score_id": str(uuid.uuid4()),
            "cycle_id": orchestration_report.get(
                "cycle_id"
            ),
            "phase": "22.20",
            "step": 8,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "execution_mode": orchestration_report.get(
                "execution_mode", "unknown"
            ),
            "provenance_verified": False,
            "score": score,
            "max_score": 100,
            "readiness": readiness,
            "summary": summary,
            "findings": findings,
            "scoring_policy": {
                "version": "poc_v1",
                "severity_weights": self.SEVERITY_WEIGHTS,
                "passing_status": "consistent",
                "default_severity": "medium",
            },
            "agent_scores": None,
            "limitations": [
                "Cycle score measures cross-agent consistency, not correctness.",
                "Per-agent scores require independently attributable outcomes.",
                "Simulated execution cannot establish production readiness.",
            ],
        }

    def save_report(self, report):
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        score_id = report["score_id"]
        uuid.UUID(score_id)

        path = self.output_dir / (
            f"assurance_score_{score_id}.json"
        )

        with path.open("x", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=2,
                default=str,
            )

        return str(path)
