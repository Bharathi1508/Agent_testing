
"""
HEAAP - Dynamic Agent Onboarding API

Endpoints:
POST /onboarding/agents
GET  /onboarding/health

The onboarding service must be configured at startup.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.discovery.onboarding_service import OnboardingService


router = APIRouter(
    prefix="/onboarding",
    tags=["Dynamic Agent Onboarding"],
)


class AgentOnboardingRequest(BaseModel):
    agent_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    provider: str
    execution_type: str
    capabilities: list[str] = Field(min_length=1)

    endpoint_name: str | None = None
    endpoint_url: str | None = None
    description: str = ""
    version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)


_onboarding_service: OnboardingService | None = None


def configure_onboarding_service(
    service: OnboardingService,
) -> None:
    """
    Register the configured onboarding service.
    Called during FastAPI application startup.
    """
    global _onboarding_service
    _onboarding_service = service


def get_onboarding_service() -> OnboardingService:
    """
    Return the configured onboarding service.
    """
    if _onboarding_service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Onboarding service is not configured. "
                "Connect the validator and registry "
                "during application startup."
            ),
        )

    return _onboarding_service


@router.get("/health")
def onboarding_health() -> dict[str, Any]:
    """
    Check whether onboarding is configured.
    """
    return {
        "service": "HEAAP Dynamic Agent Onboarding",
        "status": (
            "ready"
            if _onboarding_service is not None
            else "not_configured"
        ),
    }


@router.post("/agents")
async def onboard_agent(
    request: AgentOnboardingRequest,
    service: OnboardingService = Depends(
        get_onboarding_service
    ),
) -> dict[str, Any]:
    """
    Validate and onboard a discovered agent.

    New agents remain inactive until governance approval.
    """
    result = await service.onboard(
        request.model_dump(mode="json")
    )

    return result
