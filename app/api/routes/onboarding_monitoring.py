"""HEAAP Phase 21.3 - Onboarding monitoring API."""

from fastapi import APIRouter, HTTPException

from app.services.onboarding_monitoring_service import (
    OnboardingMonitoringService,
)


router = APIRouter(
    prefix="/api/onboarding",
    tags=["HEAAP Onboarding Monitoring"],
)


@router.get("/candidates")
def list_onboarding_candidates():
    try:
        service = OnboardingMonitoringService()

        return {
            "candidates": service.list_candidates(),
            "summary": service.get_summary(),
            "read_only": True,
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Onboarding monitoring unavailable",
        )
