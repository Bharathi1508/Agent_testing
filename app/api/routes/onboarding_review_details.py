"""HEAAP Phase 21.4 - Read-only onboarding review API."""

from fastapi import APIRouter, HTTPException

from app.services.onboarding_review_details_service import (
    OnboardingReviewDetailsService,
)


router = APIRouter(
    prefix="/api/onboarding/reviews",
    tags=["HEAAP Onboarding Reviews"],
)


@router.get("")
def list_reviews():
    try:
        service = OnboardingReviewDetailsService()
        return {
            "reviews": service.list_reviews(),
            "read_only": True,
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Onboarding review service unavailable",
        )


@router.get("/{review_id}")
def get_review(review_id: str):
    service = OnboardingReviewDetailsService()

    try:
        result = service.get_review(review_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid review identifier or document",
        )
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="Review document unavailable",
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Review not found",
        )

    return result
