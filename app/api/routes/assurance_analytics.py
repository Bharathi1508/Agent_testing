"""HEAAP Phase 21.5 - Assurance analytics API."""

from fastapi import APIRouter, HTTPException

from app.services.assurance_analytics_service import (
    AssuranceAnalyticsService,
)


router = APIRouter(
    prefix="/api/analytics",
    tags=["HEAAP Assurance Analytics"],
)


@router.get("/assurance")
def get_assurance_analytics():
    try:
        service = AssuranceAnalyticsService()
        return service.get_analytics()

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Assurance analytics unavailable",
        )
