"""HEAAP Phase 21.1 - Read-only agent registry routes."""

from fastapi import APIRouter, HTTPException

from app.services.agent_registry_dashboard_service import (
    AgentRegistryDashboardService,
)


router = APIRouter(
    prefix="/api/registry",
    tags=["HEAAP Agent Registry"],
)


@router.get("/agents")
def list_registered_agents():
    try:
        service = AgentRegistryDashboardService()
        return {
            "agents": service.list_agents(),
            "summary": service.get_summary(),
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Registry temporarily unavailable",
        )
