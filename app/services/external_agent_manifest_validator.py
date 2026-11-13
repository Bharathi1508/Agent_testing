"""Phase 18.9 - External agent manifest validation."""

import re
from urllib.parse import urlparse


SUPPORTED_FRAMEWORKS = {
    "databricks",
    "langgraph",
    "fastapi",
    "custom",
}


def validate_external_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")

    required = {
        "agent_id",
        "name",
        "framework",
        "execution_type",
        "endpoint_name",
        "capabilities",
    }

    missing = required - set(manifest)

    if missing:
        raise ValueError(
            f"Missing manifest fields: {sorted(missing)}"
        )

    agent_id = manifest["agent_id"]

    if (
        not isinstance(agent_id, str)
        or not re.fullmatch(
            r"[a-zA-Z0-9_-]{3,80}", agent_id
        )
    ):
        raise ValueError("Invalid agent ID")

    name = manifest["name"]

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Invalid agent name")

    framework = manifest["framework"]

    if framework not in SUPPORTED_FRAMEWORKS:
        raise ValueError("Unsupported framework")

    if manifest["execution_type"] != "external":
        raise ValueError("Expected external execution type")

    endpoint_name = manifest["endpoint_name"]

    if (
        not isinstance(endpoint_name, str)
        or not re.fullmatch(
            r"[a-zA-Z0-9_.-]{1,128}",
            endpoint_name,
        )
    ):
        raise ValueError("Invalid endpoint name")

    capabilities = manifest["capabilities"]

    if (
        not isinstance(capabilities, list)
        or not capabilities
        or len(capabilities) > 30
    ):
        raise ValueError("Invalid capability list")

    for capability in capabilities:
        if (
            not isinstance(capability, str)
            or not re.fullmatch(
                r"[a-z][a-z0-9_]{1,63}",
                capability,
            )
        ):
            raise ValueError("Invalid capability name")

    if len(set(capabilities)) != len(capabilities):
        raise ValueError("Duplicate capabilities")

    # Optional URL: structural validation only.
    # Do not fetch this URL during onboarding.
    endpoint_url = manifest.get("endpoint_url")

    if endpoint_url is not None:
        if not isinstance(endpoint_url, str):
            raise ValueError("Invalid endpoint URL")

        parsed = urlparse(endpoint_url)

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("Invalid HTTPS endpoint URL")

    return {
        "agent_id": agent_id,
        "name": name,
        "framework": framework,
        "execution_type": "external",
        "endpoint_name": endpoint_name,
        "declared_capabilities": sorted(capabilities),
        "manifest_valid": True,
        "capabilities_verified": False,
        "trust_status": "unverified",
        "production_approved": False,
    }
