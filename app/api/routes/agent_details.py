"""HEAAP Phase 21.2 - Read-only agent details API."""

import re

from fastapi import APIRouter, HTTPException

from app.services.agent_registry_dashboard_service import (
    AgentRegistryDashboardService,
)

from app.services.assurance_dashboard_service import (
    AssuranceDashboardService,
)


router = APIRouter(
    prefix="/api/agents",
    tags=["HEAAP Agent Details"],
)

SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


@router.get("/{agent_id}")
def get_agent_details(agent_id: str):

    if not SAFE_ID.fullmatch(agent_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid agent ID",
        )

    try:
        registry = AgentRegistryDashboardService()
        agents = registry.list_agents()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Agent registry unavailable",
        )

    agent = next(
        (
            item for item in agents
            if item.get("agent_id") == agent_id
        ),
        None,
    )

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail="Agent not found",
        )

    try:
        assurance = AssuranceDashboardService()
        history = assurance.get_agent_history(agent_id)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Assurance history unavailable",
        )

    latest = history[0] if history else None

    return {
        "agent": agent,
        "assurance": {
            "total_evaluations": len(history),
            "latest_verdict": (
                latest["agent"].get("verdict")
                if latest else None
            ),
            "latest_evaluation": (
                latest.get("created_at")
                if latest else None
            ),
            "history": history,
        },
        "governance": {
            "read_only": True,
            "execution_authorized": False,
            "production_approval_verified": False,
        },
    }
