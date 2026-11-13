
from app.registry.agent_registry import (
    list_registered_agents,
    update_agent_status
)

from app.governance.approval_store import (
    manifest_fingerprint,
    latest_assurance,
    get_approval,
    save_approval,
    revoke_approval
)


def get_agent(agent_id):
    for agent in list_registered_agents():
        if agent.agent_id == agent_id:
            return agent

    raise ValueError("Agent not registered")


def is_approved(manifest):
    approval = get_approval(manifest.agent_id)

    return bool(
        approval
        and approval["revoked"] == 0
        and approval["fingerprint"]
        == manifest_fingerprint(manifest)
    )


def approve_agent(agent_id, reviewer):
    manifest = get_agent(agent_id)
    report = latest_assurance(agent_id)

    # 1. Ensure assurance was executed
    if report is None:
        raise ValueError(
            "Run assurance tests before approval"
        )

    # 2. Ensure assurance passed
    if report["status"] != "passed":
        raise ValueError(
            "Latest assurance run did not pass"
        )

    # 3. Ensure manifest has not changed
    if report["fingerprint"] != manifest_fingerprint(manifest):
        raise ValueError(
            "Manifest changed; rerun assurance"
        )

    # 4. Save governance approval
    save_approval(manifest, reviewer)

    # 5. Activate the agent
    update_agent_status(agent_id, "active")

    return {
        "agent_id": agent_id,
        "status": "approved",
        "approved_by": reviewer,
        "registry_status": "active"
    }


def reject_agent(agent_id, reviewer):
    # 1. Confirm the agent exists
    get_agent(agent_id)

    # 2. Revoke approval
    revoke_approval(agent_id, reviewer)

    # 3. Deactivate the agent
    update_agent_status(agent_id, "inactive")

    return {
        "agent_id": agent_id,
        "status": "rejected",
        "registry_status": "inactive"
    }
