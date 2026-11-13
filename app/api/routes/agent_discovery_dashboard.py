"""
HEAAP - Agent Discovery Dashboard API

Phase 22.2: Manifest Discovery
Phase 22.5: Capability Classification

Endpoints:
GET /api/discovery/candidates
GET /api/discovery/classified-candidates
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.agent_manifest_discovery_service import (
    AgentManifestDiscoveryService,
)

from app.services.agent_capability_classifier import (
    classify_agent,
)


router = APIRouter(
    prefix="/api/discovery",
    tags=["HEAAP Agent Discovery"],
)


def _get_discovery_results() -> dict[str, Any]:
    """Retrieve candidate agents from manifest discovery."""

    try:
        result = AgentManifestDiscoveryService().discover()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Agent discovery failed. Check server logs.",
        ) from exc

    if isinstance(result, list):
        return {
            "candidates": result,
            "total": len(result),
        }

    if isinstance(result, dict):
        candidates = result.get("candidates")

        if not isinstance(candidates, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid discovery response: candidates must be a list.",
            )

        return result

    raise HTTPException(
        status_code=500,
        detail="Unexpected discovery service response.",
    )


@router.get("/candidates")
def get_discovery_candidates():
    """Return discovered agent candidates."""

    return _get_discovery_results()


@router.get("/classified-candidates")
def get_classified_candidates():
    """Classify agents without verifying or approving them."""

    discovery = _get_discovery_results()
    candidates = discovery["candidates"]

    classified_candidates = []

    for candidate in candidates:

        if not isinstance(candidate, dict):
            continue

        try:
            classification = classify_agent(candidate)

        except Exception:
            classification = {
                "agent_id": candidate.get("agent_id"),
                "classification_status": "classification_error",
                "capabilities_verified": False,
                "production_approved": False,
            }

        classified_candidates.append({
            "candidate": candidate,
            "classification": classification,
        })

    return {
        "total": len(classified_candidates),
        "classified_candidates": classified_candidates,
        "summary": {
            "total_discovered": len(candidates),
            "classification_completed": sum(
                1 for item in classified_candidates
                if item["classification"].get(
                    "classification_status"
                ) == "pending_review"
            ),
            "requires_classification": sum(
                1 for item in classified_candidates
                if item["classification"].get(
                    "classification_status"
                ) == "requires_classification"
            ),
            "classification_errors": sum(
                1 for item in classified_candidates
                if item["classification"].get(
                    "classification_status"
                ) == "classification_error"
            ),
        },
        "note": (
            "Declared capabilities are not verified. "
            "Agents are not automatically approved or executed."
        ),
    }

