"""HEAAP Phase 21.6 - Read-only assurance test evidence."""

import json
import re
from pathlib import Path


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class AssuranceTestDetailsService:

    def __init__(self, reports_dir="reports/phase20_7"):
        self.reports_dir = Path(reports_dir).resolve()

    def get_agent_tests(self, report_id, agent_id):
        if not SAFE_ID.fullmatch(report_id):
            raise ValueError("Invalid report ID")

        if not SAFE_ID.fullmatch(agent_id):
            raise ValueError("Invalid agent ID")

        path = self.reports_dir / f"{report_id}.json"

        if not path.is_file():
            return None

        with path.open("r", encoding="utf-8-sig") as file:
            report = json.load(file)

        if not isinstance(report, dict):
            raise ValueError("Invalid assurance report")

        agents = report.get("agents", [])

        if not isinstance(agents, list):
            raise ValueError("Invalid agents collection")

        agent = next(
            (
                item for item in agents
                if isinstance(item, dict)
                and item.get("agent_id") == agent_id
            ),
            None,
        )

        if agent is None:
            return None

        return {
            "report_id": report_id,
            "created_at": report.get("created_at"),
            "execution_mode": report.get("execution_mode"),
            "agent_id": agent_id,
            "verdict": agent.get("verdict", "UNKNOWN"),
            "evidence": agent,
            "read_only": True,
        }
