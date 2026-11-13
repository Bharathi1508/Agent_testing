"""
HEAAP Phase 22.11 - Assurance Dashboard API

Read-only access to Phase 22.10 evaluation reports.
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/assurance-dashboard",
    tags=["HEAAP Assurance Dashboard"],
)

REPORT_DIR = Path("reports/phase22_10")


def load_reports():
    reports = []

    if not REPORT_DIR.exists():
        return reports

    for path in sorted(REPORT_DIR.glob("evaluation_*.json")):
        try:
            with path.open("r", encoding="utf-8") as file:
                report = json.load(file)

            if not isinstance(report, dict):
                continue

            if not isinstance(report.get("summary"), dict):
                continue

            reports.append(report)

        except (OSError, json.JSONDecodeError):
            continue

    return reports


@router.get("/overview")
def assurance_overview():
    reports = load_reports()

    latest_by_agent = {}

    for report in reports:
        agent_id = report.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            continue

        previous = latest_by_agent.get(agent_id)

        if (
            previous is None
            or report.get("evaluated_at", "")
            > previous.get("evaluated_at", "")
        ):
            latest_by_agent[agent_id] = report

    agents = []

    for agent_id, report in sorted(latest_by_agent.items()):
        summary = report["summary"]

        agents.append({
            "agent_id": agent_id,
            "evaluation_id": report.get("evaluation_id"),
            "evaluated_at": report.get("evaluated_at"),
            "total_tests": summary.get("total_tests", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "errors": summary.get("errors", 0),
            "overall_pass_rate_pct": summary.get(
                "overall_pass_rate_pct", 0
            ),
        })

    total = sum(a["total_tests"] for a in agents)
    passed = sum(a["passed"] for a in agents)
    failed = sum(a["failed"] for a in agents)
    errors = sum(a["errors"] for a in agents)

    return {
        "total_agents": len(agents),
        "total_reports": len(reports),
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "overall_pass_rate_pct": (
            round(passed / total * 100, 2)
            if total else 0
        ),
        "agents": agents,
        "note": (
            "Overview uses the latest evaluation per agent. "
            "Local simulation results are not production assurance."
        ),
    }


@router.get("/reports/{evaluation_id}")
def get_assurance_report(evaluation_id: str):
    import uuid

    try:
        uuid.UUID(evaluation_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid evaluation ID",
        )

    path = REPORT_DIR / f"evaluation_{evaluation_id}.json"

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Evaluation report not found",
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            report = json.load(file)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(
            status_code=500,
            detail="Unable to read evaluation report",
        )

    return report
