
from app.registry.agent_models import AgentManifest
from app.discovery.discovery_models import DiscoveredAgent


def registry_to_discovered(
    manifest: AgentManifest,
) -> DiscoveredAgent:
    """
    Convert a registered agent manifest into
    a discovery-compatible manifest.

    Reject ambiguous or unsupported configurations.
    """

    framework = manifest.framework.strip().lower()

    if manifest.execution_type == "databricks":
        provider = "databricks"

    elif (
        manifest.execution_type == "local"
        and framework == "langgraph"
    ):
        provider = "langgraph"

    else:
        raise ValueError(
            "Cannot determine a supported provider "
            f"for framework '{manifest.framework}' "
            f"and execution type '{manifest.execution_type}'."
        )

    return DiscoveredAgent(
        agent_id=manifest.agent_id,
        agent_name=manifest.name,
        provider=provider,
        execution_type=manifest.execution_type,
        endpoint_name=manifest.endpoint_name,
        capabilities=manifest.capabilities,
        version=manifest.version,
        metadata={
            "framework": manifest.framework,
            "environment": manifest.environment,
            "registry_status": manifest.status,
        },
    )
