
from fastapi import APIRouter, HTTPException

from app.registry.agent_models import AgentManifest
from app.registry.agent_registry import (
    register_agent,
    list_registered_agents,
    find_agents_by_capability
)

router = APIRouter(
    prefix="/registry",
    tags=["Agent Registry"]
)


@router.post("/register", status_code=201)
def register(manifest: AgentManifest):
    try:
        return register_agent(manifest)
    except FileExistsError:
        raise HTTPException(
            status_code=409,
            detail="Agent ID already registered"
        )


@router.get("/agents")
def list_agents():
    return list_registered_agents()


@router.get("/search")
def search_agents(capability: str):
    return find_agents_by_capability(capability)
