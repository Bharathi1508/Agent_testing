"""HEAAP Phase 21.5 - Read-only assurance analytics."""

import json
from collections import defaultdict
from pathlib import Path


class AssuranceAnalyticsService:

    def __init__(self, reports_dir="reports/phase20_7"):
        self.reports_dir = Path(reports_dir).resolve()

    def load_reports(self):
        reports = []

        if not self.reports_dir.is_dir():
            return reports

        for path in self.reports_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8-sig") as file:
                    report = json.load(file)

                if (
                    isinstance(report, dict)
                    and isinstance(report.get("agents"), list)
                ):
                    reports.append(report)

            except (OSError, ValueError, UnicodeError):
                continue

        return sorted(
            reports,
            key=lambda item: str(item.get("created_at") or ""),
        )

    def get_analytics(self):
        reports = self.load_reports()

        agent_stats = defaultdict(
            lambda: {
                "evaluations": 0,
                "passed": 0,
                "failed": 0,
                "unsupported": 0,
            }
        )

        trend = []
        total_evaluations = 0
        passed = 0
        failed = 0
        unsupported = 0

        for report in reports:
            report_passed = 0
            report_failed = 0
            report_unsupported = 0

            for agent in report["agents"]:
                if not isinstance(agent, dict):
                    continue

                agent_id = agent.get("agent_id")

                if not isinstance(agent_id, str) or not agent_id:
                    continue

                verdict = str(
                    agent.get("verdict", "UNKNOWN")
                ).upper()

                stats = agent_stats[agent_id]
                stats["evaluations"] += 1

                total_evaluations += 1

                if verdict == "PASS":
                    stats["passed"] += 1
                    passed += 1
                    report_passed += 1

                elif verdict == "FAIL":
                    stats["failed"] += 1
                    failed += 1
                    report_failed += 1

                elif verdict == "UNSUPPORTED":
                    stats["unsupported"] += 1
                    unsupported += 1
                    report_unsupported += 1

            trend.append({
                "report_id": report.get("report_id"),
                "created_at": report.get("created_at"),
                "passed": report_passed,
                "failed": report_failed,
                "unsupported": report_unsupported,
            })

        known_outcomes = passed + failed + unsupported

        return {
            "summary": {
                "total_reports": len(reports),
                "unique_agents": len(agent_stats),
                "total_evaluations": total_evaluations,
                "passed": passed,
                "failed": failed,
                "unsupported": unsupported,
                "unknown": total_evaluations - known_outcomes,
                "pass_rate_pct": round(
                    (passed / total_evaluations) * 100, 2
                ) if total_evaluations else 0,
            },
            "agents": [
                {"agent_id": agent_id, **stats}
                for agent_id, stats in sorted(
                    agent_stats.items()
                )
            ],
            "trend": trend,
            "execution_mode": "offline_mock",
            "read_only": True,
        }
