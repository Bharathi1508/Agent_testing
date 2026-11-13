"""HEAAP Phase 21.9 - Authenticated governance decisions."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.local_reviewer_auth import (
    authenticate_reviewer,
    require_reviewer,
)
from app.services.governance_review_service import (
    GovernanceReviewService,
)


router = APIRouter(
    prefix="/api/governance",
    tags=["Governance Approval"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class DecisionRequest(BaseModel):
    decision: Literal["approved_for_next_stage", "rejected"]
    reason: str = Field(min_length=10, max_length=2000)
    expected_sha256: str = Field(
        pattern=r"^[a-fA-F0-9]{64}$"
    )


@router.post("/auth/login")
def login(request: LoginRequest):
    token = authenticate_reviewer(
        request.username,
        request.password,
    )

    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 900,
    }


@router.get("/auth/me")
def get_current_reviewer(
    reviewer=Depends(require_reviewer),
):
    return reviewer


@router.post("/reviews/{review_id}/decision")
def submit_decision(
    review_id: str,
    request: DecisionRequest,
    reviewer=Depends(require_reviewer),
):
    service = GovernanceReviewService()

    try:
        decision = service.record_decision(
            review_id=review_id,
            reviewer=reviewer["username"],
            decision=request.decision,
            reason=request.reason,
            expected_sha256=request.expected_sha256,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Review not found":
            code = 404
        elif message in (
            "Review already has a decision",
            "Review evidence has changed",
            "Review is not pending manual review",
        ):
            code = 409
        else:
            code = 400

        raise HTTPException(
            status_code=code,
            detail=message,
        )

    return {
        "message": "Governance review decision recorded",
        "decision": decision,
        "production_approved": False,
        "execution_authorized": False,
    }
