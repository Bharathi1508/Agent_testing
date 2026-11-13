"""Live HEAAP assurance reporting from the existing SQLite store."""

import json
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Query

from app.governance.approval_store import get_connection

router = APIRouter(
    prefix="/api/assurance/live",
    tags=["HEAAP Live Assurance Reporting"],
)


def read_runs(limit=100):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, agent_id, status, created_at, report_json
            FROM assurance_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    result = []

    for row in rows:
        item = dict(row)

        try:
            report = json.loads(item.pop("report_json"))
        except (ValueError, TypeError):
            report = {}

        if not isinstance(report, dict):
            report = {}

        item["report"] = report
        item["score"] = report.get("score")
        item["passed_checks"] = report.get("passed_checks")
        item["total_checks"] = report.get("total_checks")
        item["assurance_type"] = report.get("assurance_type")

        result.append(item)

    return result


@router.get("/summary")
def live_summary():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT status, report_json
            FROM assurance_runs
            """
        ).fetchall()

    passed = 0
    failed = 0
    other = 0
    scores = []
    agent_ids = set()

    for row in rows:
        status = str(row["status"]).lower()

        if status in ("passed", "pass"):
            passed += 1
        elif status in ("failed", "fail"):
            failed += 1
        else:
            other += 1

        try:
            report = json.loads(row["report_json"])
        except (ValueError, TypeError):
            continue

        if not isinstance(report, dict):
            continue

        agent_id = report.get("agent_id")

        if agent_id:
            agent_ids.add(agent_id)

        score = report.get("score")

        if isinstance(score, (int, float)) and not isinstance(score, bool):
            scores.append(score)

    return {
        "total_tests": len(rows),
        "passed": passed,
        "failed": failed,
        "other": other,
        "unique_agents": len(agent_ids),
        "average_score": round(sum(scores) / len(scores), 2)
        if scores else None,
        "execution_mode": "persisted_assurance",
        "source": "sqlite",
    }


@router.get("/reports")
def live_reports(limit: int = Query(default=50, ge=1, le=500)):
    reports = read_runs(limit)

    return {
        "reports": reports,
        "returned": len(reports),
    }


@router.get("/reports/{run_id}")
def live_report(run_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, agent_id, status, created_at, report_json
            FROM assurance_runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")

    result = dict(row)
    result["report"] = json.loads(result.pop("report_json"))

    return result


@router.get("/trend")
def live_trend():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT substr(created_at, 1, 10) AS test_date,
                   lower(status) AS status,
                   COUNT(*) AS total
            FROM assurance_runs
            GROUP BY substr(created_at, 1, 10), lower(status)
            ORDER BY test_date
            """
        ).fetchall()

    dates = defaultdict(lambda: {"passed": 0, "failed": 0, "other": 0})

    for row in rows:
        status = row["status"]

        if status in ("passed", "pass"):
            key = "passed"
        elif status in ("failed", "fail"):
            key = "failed"
        else:
            key = "other"

        dates[row["test_date"]][key] += row["total"]

    return {
        "trend": [
            {"date": date, **values}
            for date, values in sorted(dates.items())
        ]
    }
