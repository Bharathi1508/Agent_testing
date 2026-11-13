"""HEAAP Phase 21.7 - Supervisor explanation API."""

from fastapi import APIRouter, HTTPException

from app.services.supervisor_decision_explanation_service import (
    SupervisorDecisionExplanationService,
)


router = APIRouter(
    prefix="/api/supervisor/explanations",
    tags=["HEAAP Supervisor Explanations"],
)


@router.get("/{report_id}/{agent_id}")
def get_supervisor_explanation(report_id: str, agent_id: str):

    try:
        service = SupervisorDecisionExplanationService()
        result = service.explain(report_id, agent_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid report or agent identifier",
        )

    except OSError:
        raise HTTPException(
            status_code=503,
            detail="Supervisor evidence unavailable",
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Supervisor evaluation not found",
        )

    return result
