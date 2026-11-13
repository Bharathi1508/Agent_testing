"""
HEAAP Phase 22.13 - Real Agent HTTP Adapter

Reusable HTTP transport for explicitly authorized agents.

The adapter does not approve agents or validate onboarding.
Callers must enforce the HEAAP governance gate before use.

No redirects, arbitrary endpoint discovery, or automatic
execution are permitted.
"""

import ipaddress
import json
import os
import socket
from urllib.parse import urlsplit

import requests


class RealAgentHTTPAdapter:

    def __init__(
        self,
        endpoint_url,
        *,
        timeout=15,
        allowed_endpoints=None,
    ):
        if not isinstance(endpoint_url, str):
            raise ValueError("Endpoint must be a string")

        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("Invalid timeout")

        self.endpoint_url = endpoint_url
        self.timeout = timeout

        if allowed_endpoints is None:
            configured = os.getenv(
                "HEAAP_ALLOWED_ENDPOINTS", ""
            )
            allowed_endpoints = [
                value.strip()
                for value in configured.split(",")
                if value.strip()
            ]

        if self.endpoint_url not in allowed_endpoints:
            raise PermissionError(
                "Endpoint is not in the HEAAP allowlist"
            )

        parsed = urlsplit(endpoint_url)

        if parsed.scheme not in ("http", "https"):
            raise PermissionError("Unsupported URL scheme")

        if not parsed.hostname or parsed.username or parsed.password:
            raise PermissionError("Invalid endpoint URL")

        if parsed.fragment:
            raise PermissionError("URL fragments are not allowed")

        # This POC transport is restricted to literal loopback IPs.
        # External service connectivity needs a separately reviewed
        # network policy and transport.
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            raise PermissionError(
                "Only literal loopback IP endpoints are supported"
            )

        if not address.is_loopback:
            raise PermissionError(
                "Only loopback endpoints are supported"
            )

    def execute(self, test_case):
        if not isinstance(test_case, dict):
            raise ValueError("Test case must be an object")

        payload = test_case.get("request_payload")

        if not isinstance(payload, dict):
            raise ValueError(
                "Missing agent-specific request_payload"
            )

        response = requests.post(
            self.endpoint_url,
            json=payload,
            timeout=self.timeout,
            allow_redirects=False,
        )

        response.raise_for_status()

        if not 200 <= response.status_code < 300:
            raise RuntimeError(
                f"Unexpected HTTP status: {response.status_code}"
            )

        result = response.json()

        if not isinstance(result, dict):
            raise ValueError(
                "Agent response must be a JSON object"
            )

        return result
