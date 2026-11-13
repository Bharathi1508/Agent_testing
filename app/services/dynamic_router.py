
"""
HEAAP - Dynamic Agent Router

Responsibilities:
1. Discover registered agents by capability.
2. Filter inactive agents.
3. Verify governance approval.
4. Reject agents with invalid approvals.
5. Prevent ambiguous agent selection.
6. Return the selected agent manifest.

The router does NOT execute agents.
Execution is handled by agent_executor.py.
"""

import logging

from typing import Optional

from app.registry.agent_registry import (
    find_agents_by_capability,
    get_registered_agent,
)

from app.governance.approval_service import (
    is_approved,
)


logger = logging.getLogger(__name__)


# ==========================================================
# CUSTOM ROUTING EXCEPTIONS
# ==========================================================

class AgentRoutingError(Exception):
    """Base exception for agent routing errors."""
    pass


class AgentNotFoundError(AgentRoutingError):
    """No registered agent supports the capability."""
    pass


class AgentNotApprovedError(AgentRoutingError):
    """Matching agents exist but are not eligible."""
    pass


class MultipleAgentsFoundError(AgentRoutingError):
    """More than one eligible agent supports a capability."""
    pass


# ==========================================================
# CAPABILITY NORMALIZATION
# ==========================================================

def normalize_capability(capability: str) -> str:
    """
    Normalize the capability requested by the supervisor.
    """

    if not isinstance(capability, str):
        raise ValueError(
            "Capability must be a string"
        )

    normalized = capability.strip().lower()

    if not normalized:
        raise ValueError(
            "Capability cannot be empty"
        )

    return normalized


# ==========================================================
# FIND ELIGIBLE AGENTS
# ==========================================================

def get_eligible_agents(capability: str):
    """
    Retrieve agents supporting the requested capability.

    Eligibility requirements:
    - Registered
    - Active
    - Governance approved
    - Manifest fingerprint matches approval
    """

    capability = normalize_capability(capability)

    logger.info(
        "Searching for agents with capability: %s",
        capability
    )

    candidates = find_agents_by_capability(
        capability
    )

    eligible_agents = []

    for agent in candidates:

        # Re-read the manifest to use current registry state
        current_agent = get_registered_agent(
            agent.agent_id
        )

        if current_agent is None:
            logger.warning(
                "Agent no longer registered: %s",
                agent.agent_id
            )
            continue

        # STEP 1: Check registry status
        if current_agent.status != "active":
            logger.info(
                "Skipping inactive agent: %s",
                current_agent.agent_id
            )
            continue

        # STEP 2: Check governance approval
        if not is_approved(current_agent):
            logger.warning(
                "Skipping unapproved agent: %s",
                current_agent.agent_id
            )
            continue

        eligible_agents.append(
            current_agent
        )

    return eligible_agents


# ==========================================================
# RESOLVE AGENT BY CAPABILITY
# ==========================================================

def resolve_agent(
    capability: str,
    preferred_agent_id: Optional[str] = None
):
    """
    Select an approved active agent for a capability.

    If preferred_agent_id is supplied, select only that
    agent, provided it passes all governance checks.

    If multiple eligible agents are found without a
    preferred ID, raise an ambiguity error.
    """

    capability = normalize_capability(capability)

    logger.info(
        "Resolving capability: %s",
        capability
    )

    eligible_agents = get_eligible_agents(
        capability
    )

    # Optional explicit agent selection
    if preferred_agent_id:

        for agent in eligible_agents:

            if agent.agent_id == preferred_agent_id:

                logger.info(
                    "Selected preferred agent: %s",
                    agent.agent_id
                )

                return agent

        raise AgentNotApprovedError(
            f"Preferred agent '{preferred_agent_id}' "
            f"is not eligible for capability '{capability}'"
        )

    # No eligible agents
    if not eligible_agents:

        raise AgentNotApprovedError(
            f"No approved active agent supports "
            f"capability '{capability}'"
        )

    # Multiple eligible agents
    if len(eligible_agents) > 1:

        agent_ids = [
            agent.agent_id
            for agent in eligible_agents
        ]

        logger.warning(
            "Multiple eligible agents found: %s",
            agent_ids
        )

        raise MultipleAgentsFoundError(
            f"Multiple approved agents support "
            f"capability '{capability}': {agent_ids}. "
            f"Specify preferred_agent_id."
        )

    selected_agent = eligible_agents[0]

    logger.info(
        "Successfully routed to agent: %s",
        selected_agent.agent_id
    )

    return selected_agent


# ==========================================================
# CHECK CAPABILITY AVAILABILITY
# ==========================================================

def is_capability_available(capability: str) -> bool:
    """
    Return True if at least one eligible agent
    supports the requested capability.
    """

    return bool(
        get_eligible_agents(capability)
    )


# ==========================================================
# LIST AVAILABLE AGENTS FOR A CAPABILITY
# ==========================================================

def list_capability_agents(capability: str):
    """
    Return the IDs of approved active agents
    supporting the requested capability.
    """

    agents = get_eligible_agents(capability)

    return [
        {
            "agent_id": agent.agent_id,
            "agent_name": agent.agent_name,
            "execution_type": agent.execution_type,
            "status": agent.status,
        }
        for agent in agents
    ]
