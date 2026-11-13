import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class GovernanceDecisionEngine:

    POLICY_VERSION = "poc_v1"

    def __init__(
        self,
        approval_threshold=95,
        review_threshold=80,
        output_dir=None,
    ):
        if not (
            0 <= review_threshold <= approval_threshold <= 100
        ):
            raise ValueError(
                "Invalid governance score thresholds"
            )

        self.approval_threshold = approval_threshold
        self.review_threshold = review_threshold

        self.output_dir = Path(
            output_dir or "reports/phase22_20/governance"
        )

    def evaluate(self, score_report):

        score = float(score_report["score"])
        summary = score_report["summary"]
        findings = score_report.get("findings", [])

        if not 0 <= score <= 100:
            raise ValueError("Score must be between 0 and 100")

        total = int(summary.get("total", 0))
        consistent = int(summary.get("consistent", 0))
        inconsistent = int(summary.get("inconsistent", 0))
        inconclusive = int(summary.get("inconclusive", 0))
        errors = int(summary.get("errors", 0))

        if total <= 0:
            raise ValueError("Cannot govern an empty test cycle")

        if (
            min(
                consistent,
                inconsistent,
                inconclusive,
                errors,
            ) < 0
            or consistent + inconsistent + inconclusive + errors
            != total
        ):
            raise ValueError(
                "Invalid assurance summary counts"
            )

        provenance_verified = (
            score_report.get("provenance_verified") is True
        )

        critical_failures = [
            finding for finding in findings
            if finding.get("severity") == "critical"
            and finding.get("status") in {
                "inconsistent",
                "error",
            }
        ]

        reasons = []

        if critical_failures:
            decision = "blocked"
            reasons.append(
                "Critical assurance failure detected"
            )

        elif score < self.review_threshold:
            decision = "blocked"
            reasons.append(
                "Assurance score below minimum threshold"
            )

        elif not provenance_verified:
            decision = "manual_review"
            reasons.append(
                "Execution provenance is not independently verified"
            )

        elif inconclusive > 0 or errors > 0:
            decision = "manual_review"
            reasons.append(
                "Unresolved tests or execution errors exist"
            )

        elif inconsistent > 0:
            decision = "manual_review"
            reasons.append(
                "One or more consistency failures require investigation"
            )

        elif score >= self.approval_threshold:
            decision = "eligible_for_human_approval"
            reasons.append(
                "Assurance policy conditions satisfied"
            )

        else:
            decision = "manual_review"
            reasons.append(
                "Assurance score requires additional review"
            )

        return {
            "decision_id": str(uuid.uuid4()),
            "cycle_id": score_report.get("cycle_id"),
            "score_id": score_report.get("score_id"),
            "phase": "22.20",
            "step": 9,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "policy_version": self.POLICY_VERSION,
            "assurance_score": score,
            "decision": decision,
            "reasons": reasons,
            "provenance_verified": provenance_verified,
            "critical_failure_count": len(
                critical_failures
            ),
            "summary": summary,
            "policy": {
                "approval_threshold": self.approval_threshold,
                "review_threshold": self.review_threshold,
                "human_approval_required": True,
            },
            "approval_granted": False,
            "agent_status_changed": False,
        }

    def save_report(self, report):

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        decision_id = report["decision_id"]
        uuid.UUID(decision_id)

        path = self.output_dir / (
            f"governance_decision_{decision_id}.json"
        )

        with path.open("x", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=2,
                default=str,
            )

        return str(path)
