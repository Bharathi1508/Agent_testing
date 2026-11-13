"""Phase 18.9 - Read-only Databricks endpoint discovery."""

import json
import os
import ssl
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def _workspace_host():
    host = os.environ.get("DATABRICKS_HOST", "").strip()
    parsed = urlparse(host)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.hostname in {"localhost", "127.0.0.1"}
    ):
        raise ValueError("Invalid Databricks workspace host")

    # An administrator must configure a trusted workspace.
    allowed = {
        h.strip().lower()
        for h in os.environ.get(
            "HEAAP_ALLOWED_DATABRICKS_HOSTS", ""
        ).split(",")
        if h.strip()
    }

    if parsed.hostname.lower() not in allowed:
        raise PermissionError("Workspace host is not allowlisted")

    return f"https://{parsed.hostname}"


def discover_databricks_endpoints(
    *,
    live=False,
    fixture=None,
):
    """
    Offline fixture mode by default.
    Live mode lists endpoints only; it does not invoke them.
    """

    if not live:
        if fixture is None:
            fixture = {"endpoints": []}
        data = fixture
    else:
        host = _workspace_host()
        token = os.environ.get("DATABRICKS_TOKEN", "")

        if not token:
            raise ValueError("DATABRICKS_TOKEN is missing")

        request = Request(
            host + "/api/2.0/serving-endpoints",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        with urlopen(
            request,
            timeout=15,
            context=ssl.create_default_context(),
        ) as response:
            data = json.load(response)

    if not isinstance(data, dict):
        raise ValueError("Invalid discovery response")

    endpoints = data.get("endpoints", [])

    if not isinstance(endpoints, list):
        raise ValueError("Invalid endpoint list")

    candidates = []

    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            raise ValueError("Invalid endpoint entry")

        name = endpoint.get("name")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Endpoint name is missing")

        candidates.append({
            "endpoint_name": name,
            "provider": "databricks",
            "endpoint_state": endpoint.get("state"),
            "candidate_type": "unverified_serving_endpoint",
            "capabilities_verified": False,
            "registered": False,
            "activated": False,
            "invoked": False,
        })

    return {
        "source": "databricks",
        "live_discovery": live,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
