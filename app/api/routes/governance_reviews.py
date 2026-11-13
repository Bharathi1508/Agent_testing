"""HEAAP 21.8 - Read-only governance monitoring API."""

from fastapi import APIRouter, HTTPException

from app.services.governance_review_service import (
    GovernanceReviewService,
)

router = APIRouter(
    prefix="/api/governance",
    tags=["HEAAP Governance"],
)


@router.get("/reviews")
def list_governance_reviews():
    try:
        reviews = GovernanceReviewService().list_reviews()
        return {
            "reviews": reviews,
            "total": len(reviews),
            "read_only": True,
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Governance records unavailable",
        )


@router.get("/reviews/{review_id}/decision")
def get_governance_decision(review_id: str):
    service = GovernanceReviewService()

    try:
        if service.get_review(review_id) is None:
            raise HTTPException(404, "Review not found")
        return {
            "review_id": review_id,
            "decision": service.get_decision(review_id),
        }
    except ValueError:
        raise HTTPException(400, "Invalid review ID")
