"""
HEAAP Phase 22.19 - Step 10
Read-only Unified Assurance Dashboard API.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(
    prefix="/api/unified-assurance",
    tags=["Unified Assurance Dashboard"],
)

REPORT_DIR = (
    Path(__file__).resolve().parents[3]
    / "reports"
    / "phase22_19"
    / "unified"
)


def load_reports():
    if not REPORT_DIR.exists():
        return []

    reports = []

    for path in REPORT_DIR.glob(
        "unified_assurance_*.json"
    ):
        try:
            with path.open(
                "r", encoding="utf-8"
            ) as file:
                report = json.load(file)

            if not isinstance(report, dict):
                continue

            if not isinstance(
                report.get("execution_summary"), dict
            ):
                continue

            if not isinstance(
                report.get("agents"), list
            ):
                continue

            reports.append(report)

        except (OSError, ValueError):
            continue

    reports.sort(
        key=lambda r: r.get("created_at", ""),
        reverse=True,
    )

    return reports


@router.get("/overview")
def get_overview():
    reports = load_reports()

    latest = reports[0] if reports else None

    return {
        "total_reports": len(reports),
        "latest_report": latest,
        "history": [
            {
                "unified_report_id": r.get(
                    "unified_report_id"
                ),
                "created_at": r.get("created_at"),
                "evidence_type": r.get("evidence_type"),
                "source_cycle_id": r.get(
                    "source_cycle_id"
                ),
            }
            for r in reports
        ],
    }


@router.get("/reports/{report_id}")
def get_report(report_id: str):
    reports = load_reports()

    for report in reports:
        if (
            report.get("unified_report_id")
            == report_id
        ):
            return report

    raise HTTPException(
        status_code=404,
        detail="Assurance report not found",
    )
