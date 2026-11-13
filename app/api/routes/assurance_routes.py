
import logging

from fastapi import APIRouter, HTTPException

from app.assurance.assurance_engine import run_assurance
from app.assurance.manifest_adapter import registry_to_discovered
from app.registry.agent_registry import get_registered_agent
from app.governance.approval_store import save_assurance

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/assurance",
    tags=["Agent Assurance"],
)


@router.post("/test/{agent_id}")
def test_agent(agent_id: str):
    try:
        manifest = get_registered_agent(agent_id)

        if manifest is None:
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{agent_id}' not found",
            )

        discovered = registry_to_discovered(manifest)

        assurance_input = discovered.model_dump(mode="json")
        assurance_input["status"] = manifest.status

        report = run_assurance(assurance_input)

        # Preserve registry status for the caller.
        report["registry_status"] = manifest.status

        # Distinguish onboarding from existing-agent checks.
        report["evaluation_context"] = (
            "pre_activation"
            if manifest.status == "inactive"
            else "existing_active_agent"
        )

        # Persist the completed assurance report.
        # This does not approve or activate the agent.
        report = save_assurance(manifest, report)

        return report

    except HTTPException:
        raise

    except ValueError as exc:
        logger.warning(
            "Assurance validation failed for %s: %s",
            agent_id,
            exc,
        )
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        logger.exception(
            "Assurance failed for %s",
            agent_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Assurance execution failed. Check backend logs.",
        )


