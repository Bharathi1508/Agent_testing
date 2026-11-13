"""
HEAAP Phase 22.6 - Agent Onboarding Review

Purpose:
    Prepare discovered agents for onboarding review.

Important:
    This service does NOT automatically register,
    invoke, verify, or approve an agent.
"""

from typing import Any

from app.services.agent_capability_classifier import (
    classify_agent,
)


def prepare_agent_onboarding(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """
    Prepare an agent candidate for onboarding review.

    Registration must occur separately through the
    existing approval-enforcing persistent registry.
    """

    if not isinstance(candidate, dict):
        raise ValueError("Candidate must be a dictionary")

    agent_id = candidate.get("agent_id")

    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("Missing agent_id")

    classification = classify_agent(candidate)

    return {
        "agent_id": agent_id,
        "name": candidate.get("name"),
        "framework": candidate.get("framework"),
        "execution_type": candidate.get("execution_type"),
        "endpoint_name": candidate.get("endpoint_name"),
        "declared_capabilities": classification[
            "declared_capabilities"
        ],
        "suggested_test_suites": classification[
            "suggested_test_suites"
        ],
        "unmapped_capabilities": classification[
            "unmapped_capabilities"
        ],
        "classification_status": classification[
            "classification_status"
        ],
        "capabilities_verified": False,
        "trust_status": "unverified",
        "production_approved": False,
        "onboarding_status": "pending_review",
        "registration_performed": False,
    }
