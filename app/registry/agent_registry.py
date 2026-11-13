
"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Agent Registry

Responsibilities:
1. Register new agents.
2. Store agent manifests as JSON files.
3. List registered agents.
4. Retrieve agents by ID.
5. Search agents by capability.
6. Activate or deactivate agents.
"""

import json
import os
import re
import tempfile

from pathlib import Path
from typing import List, Optional

from app.registry.agent_models import AgentManifest


# ==========================================
# Registry configuration
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

REGISTRY_PATH = BASE_DIR / "manifests"

REGISTRY_PATH.mkdir(
    parents=True,
    exist_ok=True
)

AGENT_ID_PATTERN = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9_-]*$"
)


# ==========================================
# Validate agent ID
# ==========================================

def validate_agent_id(agent_id: str) -> str:
    """
    Prevent invalid agent IDs and path traversal.
    """

    if not AGENT_ID_PATTERN.fullmatch(agent_id):
        raise ValueError(
            "Invalid agent ID. Use letters, "
            "numbers, underscores or hyphens."
        )

    return agent_id


# ==========================================
# Get manifest file path
# ==========================================

def get_manifest_path(agent_id: str) -> Path:
    """
    Return the JSON file path for an agent.
    """

    validate_agent_id(agent_id)

    return REGISTRY_PATH / f"{agent_id}.json"


# ==========================================
# Register agent
# ==========================================

def register_agent(manifest: AgentManifest) -> dict:
    """
    Register an agent as inactive.

    Newly registered agents must pass
    assurance testing and governance approval
    before activation.
    """

    manifest = AgentManifest.model_validate(
        manifest.model_dump()
    )

    validate_agent_id(manifest.agent_id)

    file_path = get_manifest_path(
        manifest.agent_id
    )

    if file_path.exists():
        raise ValueError(
            f"Agent '{manifest.agent_id}' "
            "is already registered."
        )

    # Never activate an agent at registration.
    manifest = manifest.model_copy(
        update={"status": "inactive"}
    )

    with file_path.open(
        "x",
        encoding="utf-8"
    ) as file:
        json.dump(
            manifest.model_dump(),
            file,
            indent=4
        )

    return {
        "status": "registered",
        "agent_id": manifest.agent_id,
        "registry_status": "inactive",
        "message": (
            "Agent registered successfully. "
            "Assurance testing and approval required."
        )
    }


# ==========================================
# Get agent by ID
# ==========================================

def get_registered_agent(
    agent_id: str
) -> Optional[AgentManifest]:
    """
    Retrieve an agent by its registered ID.

    Returns None if not found.
    """

    file_path = get_manifest_path(agent_id)

    if not file_path.is_file():
        return None

    with file_path.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    manifest = AgentManifest.model_validate(data)

    if manifest.agent_id != agent_id:
        raise ValueError(
            "Agent ID does not match manifest filename."
        )

    return manifest


# ==========================================
# List registered agents
# ==========================================

def list_registered_agents() -> List[AgentManifest]:
    """
    Load all valid registered agents from
    the manifests directory.
    """

    agents = []

    for file_path in sorted(
        REGISTRY_PATH.glob("*.json")
    ):
        try:
            data = json.loads(
                file_path.read_text(
                    encoding="utf-8"
                )
            )

            manifest = AgentManifest.model_validate(
                data
            )

            # Prevent filename/manifest mismatch.
            if file_path.stem != manifest.agent_id:
                raise ValueError(
                    "Manifest filename and agent ID mismatch"
                )

            agents.append(manifest)

        except (ValueError, OSError) as exc:
            # Report malformed manifests instead
            # of silently losing them.
            print(
                f"[Registry] Skipping invalid manifest "
                f"{file_path.name}: {exc}"
            )

    return agents


# ==========================================
# Find agents by capability
# ==========================================

def find_agents_by_capability(
    capability: str
) -> List[AgentManifest]:
    """
    Return active agents supporting
    the requested capability.

    Governance approval must additionally
    be checked by the Dynamic Supervisor.
    """

    if not capability.strip():
        raise ValueError(
            "Capability cannot be empty."
        )

    matching_agents = []

    for agent in list_registered_agents():

        if agent.status != "active":
            continue

        supported_capabilities = {
            item.casefold()
            for item in agent.capabilities
        }

        if capability.strip().casefold() in supported_capabilities:
            matching_agents.append(agent)

    return matching_agents


# ==========================================
# Update agent status
# ==========================================

def update_agent_status(
    agent_id: str,
    status: str
) -> AgentManifest:
    """
    Update an agent's registry status.

    Intended for trusted governance services,
    not for unrestricted public API access.
    """

    if status not in ("active", "inactive"):
        raise ValueError(
            "Status must be 'active' or 'inactive'."
        )

    file_path = get_manifest_path(agent_id)

    if not file_path.is_file():
        raise ValueError(
            f"Agent '{agent_id}' is not registered."
        )

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError(
            f"Agent '{agent_id}' not found."
        )

    updated_manifest = manifest.model_copy(
        update={"status": status}
    )

    # Validate before saving.
    updated_manifest = AgentManifest.model_validate(
        updated_manifest.model_dump()
    )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            dir=REGISTRY_PATH,
            delete=False
        ) as temp_file:

            temp_path = temp_file.name

            json.dump(
                updated_manifest.model_dump(),
                temp_file,
                indent=4
            )

        # Atomic replacement on the same filesystem.
        os.replace(
            temp_path,
            file_path
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

    return updated_manifest
