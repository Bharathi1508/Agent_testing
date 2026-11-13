
import os
import secrets

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException
)

from app.governance.approval_service import (
    approve_agent,
    reject_agent,
    get_agent,
    is_approved
)

from app.governance.approval_store import (
    latest_assurance,
    get_history
)


# ==========================================
# Load environment variables
# ==========================================

load_dotenv()


# ==========================================
# Initialize API Router
# ==========================================

router = APIRouter(
    prefix="/governance",
    tags=["Agent Governance"]
)


# ==========================================
# Reviewer authentication
# ==========================================

def require_reviewer(
    x_reviewer_token: str = Header(default="")
):
    """
    Validate the reviewer token supplied
    through the x-reviewer-token header.
    """

    expected_token = os.getenv(
        "HEAAP_REVIEWER_TOKEN"
    )

    if not expected_token:
        raise HTTPException(
            status_code=503,
            detail="Reviewer token is not configured"
        )

    if not secrets.compare_digest(
        x_reviewer_token,
        expected_token
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid reviewer token"
        )

    return os.getenv(
        "HEAAP_REVIEWER_ID",
        "local_poc_reviewer"
    )


# ==========================================
# 1. Governance Health Check
# ==========================================

@router.get("/health")
def governance_health():
    """
    Verify that the governance API is running.
    """

    return {
        "status": "running",
        "service": "HEAAP Agent Governance",
        "phase": 8
    }


# ==========================================
# 2. Approve Agent
# ==========================================

@router.post("/approve/{agent_id}")
def approve_registered_agent(
    agent_id: str,
    reviewer: str = Depends(require_reviewer)
):
    """
    Approve an agent after successful
    assurance testing.

    Approval is handled by approval_service.
    """

    try:
        result = approve_agent(
            agent_id,
            reviewer
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# ==========================================
# 3. Reject / Revoke Agent
# ==========================================

@router.post("/reject/{agent_id}")
def reject_registered_agent(
    agent_id: str,
    reviewer: str = Depends(require_reviewer)
):
    """
    Reject or revoke an agent's approval.
    """

    try:
        result = reject_agent(
            agent_id,
            reviewer
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# ==========================================
# 4. Get Agent Governance Status
# ==========================================

@router.get("/status/{agent_id}")
def get_agent_governance_status(
    agent_id: str,
    reviewer: str = Depends(require_reviewer)
):
    """
    Return the current approval and
    assurance status of an agent.
    """

    try:
        manifest = get_agent(agent_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    assurance_report = latest_assurance(
        agent_id
    )

    approved = is_approved(
        manifest
    )

    return {
        "agent_id": agent_id,
        "agent_name": manifest.name,
        "agent_version": manifest.version,
        "execution_type": manifest.execution_type,
        "registry_status": manifest.status,
        "approved": approved,
        "latest_assurance": assurance_report
    }


# ==========================================
# 5. Get Agent Audit History
# ==========================================

@router.get("/history/{agent_id}")
def get_agent_audit_history(
    agent_id: str,
    reviewer: str = Depends(require_reviewer)
):
    """
    Retrieve recorded governance events
    for an agent.
    """

    try:
        get_agent(agent_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    events = get_history(
        agent_id
    )

    return {
        "agent_id": agent_id,
        "total_events": len(events),
        "events": events
    }
