"""HEAAP Phase 20.9 - Assurance dashboard routes."""

from fastapi import APIRouter, HTTPException

from app.services.assurance_dashboard_service import (
    AssuranceDashboardService,
)


router = APIRouter(
    prefix="/api/assurance",
    tags=["HEAAP Assurance Dashboard"],
)


service = AssuranceDashboardService()


@router.get("/summary")
def get_assurance_summary():
    return service.get_summary()


@router.get("/reports")
def list_assurance_reports():
    return {
        "reports": service.list_reports()
    }


@router.get("/reports/{report_id}")
def get_assurance_report(report_id: str):
    try:
        report = service.get_report(report_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid report ID",
        )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report


@router.get("/agents/{agent_id}/history")
def get_agent_history(agent_id: str):
    try:
        history = service.get_agent_history(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid agent ID",
        )

    return {
        "agent_id": agent_id,
        "history": history,
        "total_evaluations": len(history),
    }
