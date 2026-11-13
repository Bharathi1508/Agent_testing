
"""
HEAAP - Dynamic Supervisor API Routes

Provides endpoints for:
1. Executing approved agents dynamically.
2. Checking capability availability.
3. Listing eligible agents for a capability.

All execution requests go through the
Dynamic Supervisor Service and governance checks.
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
    SupervisorAuthorizationError,
    SupervisorExecutionError,
)

from app.services.dynamic_router import (
    AgentRoutingError,
    AgentNotApprovedError,
    AgentNotFoundError,
    MultipleAgentsFoundError,
    is_capability_available,
    list_capability_agents,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/supervisor",
    tags=["Dynamic Supervisor"]
)


# ==========================================================
# REQUEST MODEL
# ==========================================================

class SupervisorRequest(BaseModel):

    capability: str = Field(
        ...,
        min_length=1,
        description="Capability required for agent execution"
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Input payload passed to selected agent"
    )

    preferred_agent_id: Optional[str] = Field(
        default=None,
        description="Optional agent ID for explicit selection"
    )


# ==========================================================
# EXECUTE DYNAMIC AGENT
# ==========================================================

@router.post("/execute")
def execute_supervisor(request: SupervisorRequest):
    """
    Dynamically discover, validate and execute
    an approved active agent.
    """

    try:
        result = execute_supervisor_request(
            capability=request.capability,
            payload=request.payload,
            preferred_agent_id=request.preferred_agent_id
        )

        return result

    except SupervisorAuthorizationError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc)
        )

    except AgentNotApprovedError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc)
        )

    except AgentNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except MultipleAgentsFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc)
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except SupervisorExecutionError:
        logger.exception(
            "Supervisor execution failed"
        )

        raise HTTPException(
            status_code=502,
            detail="Selected agent execution failed"
        )

    except AgentRoutingError:
        logger.exception(
            "Agent routing failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Agent routing failed"
        )

    except Exception:
        logger.exception(
            "Unexpected supervisor error"
        )

        raise HTTPException(
            status_code=500,
            detail="Internal supervisor error"
        )


# ==========================================================
# CHECK CAPABILITY AVAILABILITY
# ==========================================================

@router.get("/capabilities/{capability}/available")
def check_capability(capability: str):
    """
    Check whether an approved active agent
    supports the requested capability.
    """

    try:
        available = is_capability_available(
            capability
        )

        return {
            "capability": capability,
            "available": available
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception:
        logger.exception(
            "Capability availability check failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Capability availability check failed"
        )


# ==========================================================
# LIST AGENTS SUPPORTING A CAPABILITY
# ==========================================================

@router.get("/capabilities/{capability}/agents")
def get_capability_agents(capability: str):
    """
    List approved active agents supporting
    the requested capability.
    """

    try:
        agents = list_capability_agents(
            capability
        )

        return {
            "capability": capability,
            "count": len(agents),
            "agents": agents
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception:
        logger.exception(
            "Failed to list capability agents"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve eligible agents"
        )
