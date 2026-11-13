"""
HEAAP Phase 15.5
Multi-Agent Assurance Report Service
"""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def generate_multi_agent_report(agent_reports):

    if not isinstance(agent_reports, list):
        raise ValueError("agent_reports must be a list")

    if not agent_reports:
        raise ValueError("No agent reports provided")

    summary = Counter()
    agent_summaries = []

    for report in agent_reports:

        results = report.get("results", [])

        counts = Counter(
            item.get("status", "error")
            for item in results
        )

        total = len(results)

        agent_summaries.append({
            "agent_id": report["agent_id"],
            "total_tests": total,
            "passed_tests": counts["passed"],
            "failed_tests": counts["failed"],
            "error_tests": counts["error"],
            "inconclusive_tests": counts["inconclusive"],
            "status": (
                "passed"
                if total > 0 and counts["passed"] == total
                else "incomplete"
            ),
        })

        summary.update(counts)

    total_tests = sum(summary.values())

    final_report = {
        "platform": "HEAAP",
        "assurance_type": "multi_agent_adversarial",
        "phase": "15.5",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_agents": len(agent_summaries),
        "total_tests": total_tests,
        "passed_tests": summary["passed"],
        "failed_tests": summary["failed"],
        "error_tests": summary["error"],
        "inconclusive_tests": summary["inconclusive"],
        "overall_status": (
            "passed"
            if total_tests > 0
            and summary["passed"] == total_tests
            else "incomplete"
        ),
        "agents": agent_summaries,
    }

    return final_report


def save_multi_agent_report(report):

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d_%H%M%S_%f")

    path = REPORT_DIR / (
        f"multi_agent_assurance_{timestamp}.json"
    )

    path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    return path
