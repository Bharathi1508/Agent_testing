
from fastapi import APIRouter, HTTPException

from app.assurance.assurance_engine import (
    run_assurance
)


router = APIRouter(
    prefix="/assurance",
    tags=["Agent Assurance"]
)


@router.post("/test/{agent_id}")
def test_agent(agent_id: str):
    try:
        return run_assurance(agent_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )
