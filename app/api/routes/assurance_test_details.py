"""HEAAP Phase 21.6 - Test evidence API."""

from fastapi import APIRouter, HTTPException

from app.services.assurance_test_details_service import (
    AssuranceTestDetailsService,
)


router = APIRouter(
    prefix="/api/assurance/tests",
    tags=["HEAAP Test Evidence"],
)


@router.get("/{report_id}/{agent_id}")
def get_test_evidence(report_id: str, agent_id: str):
    try:
        service = AssuranceTestDetailsService()
        result = service.get_agent_tests(report_id, agent_id)

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid report or agent identifier",
        )

    except OSError:
        raise HTTPException(
            status_code=503,
            detail="Assurance evidence unavailable",
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Test evidence not found",
        )

    return result
