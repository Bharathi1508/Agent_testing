
import json
from pathlib import Path

from app.registry.agent_models import AgentManifest


REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / "manifests"
)

REGISTRY_PATH.mkdir(parents=True, exist_ok=True)


def register_agent(manifest: AgentManifest):
    file_path = REGISTRY_PATH / f"{manifest.agent_id}.json"

    # Prevent accidental duplicate registration
    with file_path.open("x", encoding="utf-8") as file:
        json.dump(
            manifest.model_dump(),
            file,
            indent=4
        )

    return {
        "status": "registered",
        "agent_id": manifest.agent_id
    }


def list_registered_agents():
    agents = []

    for file_path in REGISTRY_PATH.glob("*.json"):
        try:
            data = json.loads(
                file_path.read_text(encoding="utf-8")
            )

            agent = AgentManifest.model_validate(data)
            agents.append(agent)

        except (ValueError, OSError):
            # Ignore invalid manifest files
            continue

    return agents


def find_agents_by_capability(capability: str):
    matching_agents = []

    for agent in list_registered_agents():
        if agent.status != "active":
            continue

        capabilities = {
            item.lower()
            for item in agent.capabilities
        }

        if capability.lower() in capabilities:
            matching_agents.append(agent)

    return matching_agents

def find_agents_by_capability(capability: str):
    """
    Find active registered agents supporting
    the requested capability.
    """

    agents = list_registered_agents()
    matching_agents = []

    for agent in agents:
        if agent.status != "active":
            continue

        supported_capabilities = [
            item.lower()
            for item in agent.capabilities
        ]

        if capability.lower() in supported_capabilities:
            matching_agents.append(agent)

    return matching_agents

