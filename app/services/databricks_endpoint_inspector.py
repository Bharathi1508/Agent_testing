"""HEAAP Phase 20.4 - Databricks endpoint inspection."""

import re

SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def inspect_databricks_endpoints(endpoints):
    if not isinstance(endpoints, list):
        raise ValueError("Endpoints must be a list")

    results = []
    seen = set()

    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            raise ValueError("Invalid endpoint record")

        name = endpoint.get("name")

        if (
            not isinstance(name, str)
            or not SAFE_NAME.fullmatch(name)
        ):
            raise ValueError("Invalid endpoint name")

        if name in seen:
            raise ValueError("Duplicate endpoint name")

        seen.add(name)

        results.append({
            "provider": "databricks",
            "agent_id": "dbx_" + name,
            "endpoint_name": name,
            "declared_capabilities": [],
            "capabilities_verified": False,
            "discovery_status": "pending_capability_identification",
            "execution_authorized": False,
            "automatically_registered": False,
        })

    return results
