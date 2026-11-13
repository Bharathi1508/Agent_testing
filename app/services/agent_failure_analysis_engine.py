"""
HEAAP Phase 22.19 - Step 8
Automated Agent Failure Analysis Engine

Deterministic failure classification.
No external calls or LLM dependency.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class AgentFailureAnalysisEngine:

    ERROR_RULES = {
        "PERMISSION_DENIED": (
            "authorization_failure",
            "high",
            "Review agent permissions and approval."
        ),
        "UNAUTHORIZED": (
            "authorization_failure",
            "high",
            "Check authentication and access policy."
        ),
        "TIMEOUT": (
            "execution_timeout",
            "medium",
            "Check endpoint latency and timeouts."
        ),
        "SYNTAX_ERROR": (
            "sql_generation_error",
            "high",
            "Validate generated SQL syntax."
        ),
        "TABLE_OR_VIEW_NOT_FOUND": (
            "metadata_or_sql_reference_error",
            "high",
            "Verify catalog, schema and table names."
        ),
        "COLUMN_NOT_FOUND": (
            "metadata_or_sql_reference_error",
            "high",
            "Verify the referenced column."
        ),
        "INVALID_RESPONSE": (
            "invalid_agent_response",
            "medium",
            "Check the agent response contract."
        ),
    }

    def classify(self, result):
        status = str(
            result.get("status", "")
        ).lower()

        if status in ("passed", "pass"):
            return None

        if status not in (
            "failed", "fail", "error", "blocked"
        ):
            return None

        error_code = str(
            result.get("error_code") or ""
        ).upper()

        error_message = str(
            result.get("error")
            or result.get("reason")
            or ""
        )

        if error_code in self.ERROR_RULES:
            category, severity, action = (
                self.ERROR_RULES[error_code]
            )

        elif "timeout" in error_message.lower():
            category = "execution_timeout"
            severity = "medium"
            action = "Inspect agent response latency."

        elif "permission" in error_message.lower():
            category = "authorization_failure"
            severity = "high"
            action = "Review access permissions."

        elif "syntax" in error_message.lower():
            category = "sql_generation_error"
            severity = "high"
            action = "Inspect the generated SQL."

        elif "metadata" in error_message.lower():
            category = "metadata_mismatch"
            severity = "medium"
            action = "Compare with trusted metadata."

        elif status == "blocked":
            category = "authorization_or_policy_block"
            severity = "high"
            action = "Inspect governance decision."

        else:
            category = "unclassified_failure"
            severity = "medium"
            action = "Review the original test evidence."

        return {
            "agent_id": result.get("agent_id"),
            "test_id": result.get("test_id"),
            "status": status,
            "category": category,
            "severity": severity,
            "error_code": error_code or None,
            "evidence": error_message[:500],
            "recommended_action": action,
        }

    def analyze(self, results):
        if not isinstance(results, list):
            raise ValueError(
                "Results must be a list"
            )

        findings = []

        for result in results:
            finding = self.classify(result)

            if finding is not None:
                findings.append(finding)

        categories = {}

        for finding in findings:
            category = finding["category"]
            categories[category] = (
                categories.get(category, 0) + 1
            )

        return {
            "analysis_id": str(uuid.uuid4()),
            "phase": "22.19-step8",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": {
                "records_analyzed": len(results),
                "findings": len(findings),
                "categories": categories,
            },
            "findings": findings,
        }

    def save_report(
        self,
        report,
        output_dir="reports/phase22_19/failures",
    ):
        folder = Path(output_dir)
        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        analysis_id = report["analysis_id"]
        uuid.UUID(analysis_id)

        path = folder / (
            f"failure_analysis_{analysis_id}.json"
        )

        with path.open(
            "x", encoding="utf-8"
        ) as file:
            json.dump(report, file, indent=2)

        return str(path)
