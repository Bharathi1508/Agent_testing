"""HEAAP Phase 20.9 - Read-only assurance dashboard service."""

import json
import re
from pathlib import Path


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class AssuranceDashboardService:

    def __init__(self, reports_dir="reports/phase20_7"):
        self.reports_dir = Path(reports_dir).resolve()

    def list_reports(self):
        if not self.reports_dir.is_dir():
            return []

        reports = []

        for path in self.reports_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8-sig") as file:
                    report = json.load(file)

                if (
                    isinstance(report, dict)
                    and report.get("phase") == "20.7"
                    and isinstance(report.get("agents"), list)
                    and isinstance(report.get("report_id"), str)
                    and SAFE_ID.fullmatch(report["report_id"])
                ):
                    reports.append(report)

            except (OSError, ValueError, UnicodeError):
                continue

        return sorted(
            reports,
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

    def get_report(self, report_id):
        if not SAFE_ID.fullmatch(report_id):
            raise ValueError("Invalid report ID")

        for report in self.list_reports():
            if report["report_id"] == report_id:
                return report

        return None

    def get_agent_history(self, agent_id):
        if not SAFE_ID.fullmatch(agent_id):
            raise ValueError("Invalid agent ID")

        history = []

        for report in self.list_reports():
            for agent in report["agents"]:
                if (
                    isinstance(agent, dict)
                    and agent.get("agent_id") == agent_id
                ):
                    history.append({
                        "report_id": report["report_id"],
                        "created_at": report.get("created_at"),
                        "agent": agent,
                    })

        return history

    def get_summary(self):
        reports = self.list_reports()

        total_evaluations = 0
        passed = 0
        failed = 0
        unsupported = 0
        agent_ids = set()

        for report in reports:
            for agent in report["agents"]:
                if not isinstance(agent, dict):
                    continue

                agent_id = agent.get("agent_id")

                if isinstance(agent_id, str):
                    agent_ids.add(agent_id)

                total_evaluations += 1

                verdict = agent.get("verdict")

                if verdict == "PASS":
                    passed += 1
                elif verdict == "FAIL":
                    failed += 1
                else:
                    unsupported += 1

        return {
            "total_reports": len(reports),
            "unique_agents": len(agent_ids),
            "total_agent_evaluations": total_evaluations,
            "passed": passed,
            "failed": failed,
            "unsupported": unsupported,
            "execution_mode": "offline_mock",
            "production_approved": False,
        }
