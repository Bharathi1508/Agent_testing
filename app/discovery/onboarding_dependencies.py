
"""
HEAAP - Onboarding Dependency Adapters

Connects the onboarding service to the existing
Agent Registry without modifying registry logic.
"""

from typing import Any

from app.discovery.onboarding_service import OnboardingService

from app.registry.agent_models import AgentManifest

from app.registry.agent_registry import (
    get_registered_agent,
    register_agent,
)


def registry_lookup(agent_id: str) -> Any:
    """
    Check whether an agent is already registered.
    """
    return get_registered_agent(agent_id)


def registry_register(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert the normalized onboarding manifest
    into the registry's AgentManifest model.

    New agents must remain inactive.
    """

    safe_manifest = manifest.copy()

    safe_manifest["status"] = "inactive"

    # Do not trust approval flags supplied by agents.
    safe_manifest.pop("approved", None)

    agent = AgentManifest.model_validate(
        safe_manifest
    )

    return register_agent(agent)


def create_onboarding_service(
    validator,
    assurance_runner=None,
) -> OnboardingService:
    """
    Build the onboarding service using the
    existing registry functions.

    The validator and assurance runner are
    supplied by their respective modules.
    """

    return OnboardingService(
        validator=validator,
        registry_lookup=registry_lookup,
        registry_register=registry_register,
        assurance_runner=assurance_runner,
    )
