
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from app.registry.agent_registry import (
    get_agents,
    get_agent,
    register_agent
)

router = APIRouter(prefix="/registry", tags=["Agent Registry"])


class AgentRegistration(BaseModel):
    agent_id: str
    name: str
    runtime: Literal["local"]
    framework: str
    protocol: Literal["rest"]
    endpoint: str
    capabilities: list[str] = Field(min_length=1)


@router.get("/agents")
def list_agents():
    return {"agents": get_agents()}


@router.get("/agents/{agent_id}")
def find_agent(agent_id: str):
    agent = get_agent(agent_id)

    if not agent:
        raise HTTPException(404, "Agent not found")

    return agent


@router.post("/agents")
def add_agent(agent: AgentRegistration):
    try:
        return register_agent(agent.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
