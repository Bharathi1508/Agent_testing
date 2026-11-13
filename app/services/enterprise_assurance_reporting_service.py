import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path


class EnterpriseAssuranceReportingService:

    def __init__(self, output_dir=None):
        self.output_dir = Path(
            output_dir or "reports/phase22_20/enterprise"
        )

    def build_report(
        self,
        orchestration_report,
        score_report,
        governance_report,
    ):
        cycle_id = orchestration_report.get("cycle_id")

        if not cycle_id:
            raise ValueError("Orchestration cycle ID is missing")

        if score_report.get("cycle_id") != cycle_id:
            raise ValueError("Scoring report cycle mismatch")

        if governance_report.get("cycle_id") != cycle_id:
            raise ValueError("Governance report cycle mismatch")

        if (
            governance_report.get("score_id")
            != score_report.get("score_id")
        ):
            raise ValueError("Governance score ID mismatch")

        tests = orchestration_report.get("results", [])
        counts = Counter(
            item.get("status") for item in tests
        )

        expected_summary = {
            "total": len(tests),
            "consistent": counts["consistent"],
            "inconsistent": counts["inconsistent"],
            "inconclusive": counts["inconclusive"],
            "errors": counts["error"],
        }

        if (
            score_report.get("summary")
            != expected_summary
        ):
            raise ValueError(
                "Scoring summary does not match test results"
            )

        if (
            governance_report.get("summary")
            != expected_summary
        ):
            raise ValueError(
                "Governance summary does not match test results"
            )

        if (
            float(governance_report["assurance_score"])
            != float(score_report["score"])
        ):
            raise ValueError(
                "Governance score does not match scoring report"
            )

        execution_mode = orchestration_report.get(
            "execution_mode", "unknown"
        )

        provenance_verified = (
            orchestration_report.get("provenance_verified") is True
            and score_report.get("provenance_verified") is True
            and governance_report.get("provenance_verified") is True
        )

        findings = []

        for test in tests:
            if test.get("status") != "consistent":
                findings.append({
                    "test_id": test.get("test_id"),
                    "question": test.get("question"),
                    "status": test.get("status"),
                    "error_message": test.get("error_message"),
                    "consistency_report": test.get(
                        "consistency_report"
                    ),
                })

        return {
            "report_id": str(uuid.uuid4()),
            "report_type": "enterprise_assurance",
            "phase": "22.20",
            "step": 10,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "cycle_id": cycle_id,
            "executive_summary": {
                "total_tests": len(tests),
                "consistent": counts["consistent"],
                "inconsistent": counts["inconsistent"],
                "inconclusive": counts["inconclusive"],
                "errors": counts["error"],
                "assurance_score": score_report["score"],
                "governance_decision": governance_report["decision"],
                "approval_granted": governance_report.get(
                    "approval_granted", False
                ),
            },
            "execution": {
                "mode": execution_mode,
                "provenance_verified": provenance_verified,
                "agent_workflow": [
                    "metadata_agent",
                    "sql_agent",
                    "sql_validator_agent",
                ],
            },
            "scoring": {
                "policy": score_report.get("scoring_policy"),
                "readiness": score_report.get("readiness"),
                "agent_scores": score_report.get("agent_scores"),
            },
            "governance": {
                "policy_version": governance_report.get(
                    "policy_version"
                ),
                "decision": governance_report["decision"],
                "reasons": governance_report.get("reasons", []),
                "agent_status_changed": governance_report.get(
                    "agent_status_changed", False
                ),
            },
            "test_results": tests,
            "findings": findings,
            "source_references": {
                "score_id": score_report["score_id"],
                "decision_id": governance_report["decision_id"],
            },
            "limitations": [
                "Cross-agent consistency does not prove factual correctness.",
                "Per-agent accuracy has not been independently established.",
                "Simulated results do not establish production readiness.",
                "This report does not grant agent approval.",
            ],
        }

    def save_report(self, report):
        self.output_dir.mkdir(
            parents=True, exist_ok=True
        )

        report_id = report["report_id"]
        uuid.UUID(report_id)

        json_path = self.output_dir / (
            f"enterprise_assurance_{report_id}.json"
        )

        html_path = self.output_dir / (
            f"enterprise_assurance_{report_id}.html"
        )

        with json_path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2, default=str)

        summary = report["executive_summary"]
        governance = report["governance"]
        execution = report["execution"]

        def safe(value):
            return escape(str(value))

        rows = "".join(
            "<tr>"
            f"<td>{safe(t.get('test_id'))}</td>"
            f"<td>{safe(t.get('question'))}</td>"
            f"<td>{safe(t.get('status'))}</td>"
            "</tr>"
            for t in report["test_results"]
        )

        reasons = "".join(
            f"<li>{safe(reason)}</li>"
            for reason in governance["reasons"]
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HEAAP Enterprise Assurance Report</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 40px auto;
    max-width: 1100px;
    color: #1f2937;
    line-height: 1.5;
}}
h1, h2 {{ color: #17365d; }}
table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 16px;
}}
th, td {{
    border: 1px solid #d1d5db;
    padding: 10px;
    text-align: left;
}}
th {{ background: #edf2f7; }}
.metric {{
    display: inline-block;
    padding: 18px;
    margin: 8px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
}}
.warning {{
    background: #fff7ed;
    padding: 12px;
    border-left: 4px solid #d97706;
}}
</style>
</head>
<body>
<h1>HEAAP Enterprise Assurance Report</h1>
<p><strong>Cycle:</strong> {safe(report['cycle_id'])}</p>
<p><strong>Generated:</strong> {safe(report['generated_at'])}</p>

<h2>Executive Summary</h2>
<div class="metric">Tests: {safe(summary['total_tests'])}</div>
<div class="metric">Score: {safe(summary['assurance_score'])}/100</div>
<div class="metric">Decision: {safe(summary['governance_decision'])}</div>

<h2>Test Outcomes</h2>
<p>Consistent: {safe(summary['consistent'])} |
Inconsistent: {safe(summary['inconsistent'])} |
Inconclusive: {safe(summary['inconclusive'])} |
Errors: {safe(summary['errors'])}</p>

<h2>Execution Evidence</h2>
<p>Mode: {safe(execution['mode'])}</p>
<p>Provenance verified: {safe(execution['provenance_verified'])}</p>
<p>Approval granted: {safe(summary['approval_granted'])}</p>

<h2>Governance Reasons</h2>
<ul>{reasons}</ul>

<h2>Individual Test Results</h2>
<table>
<thead>
<tr><th>Test ID</th><th>Business Question</th><th>Status</th></tr>
</thead>
<tbody>{rows}</tbody>
</table>

<h2>Assurance Limitations</h2>
<div class="warning">
<p>Consistency is not proof of correctness.
Simulated execution is not production assurance.
This report does not grant approval.</p>
</div>
</body>
</html>"""

        with html_path.open("x", encoding="utf-8") as file:
            file.write(html)

        return {
            "json": str(json_path),
            "html": str(html_path),
        }
