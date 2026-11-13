from datetime import datetime, timezone
from urllib.parse import urlparse
import ipaddress
import socket

import httpx


class RealAgentConnectionValidator:

    def __init__(self, allowed_endpoints=None):
        self.allowed_endpoints = set(
            allowed_endpoints or []
        )

    def validate(self, agent_id, endpoint):
        result = {
            "agent_id": agent_id,
            "endpoint": endpoint,
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": "blocked",
            "reachable": False,
            "http_status": None,
            "reason": None,
        }

        if endpoint not in self.allowed_endpoints:
            result["reason"] = (
                "Endpoint is not explicitly allowlisted"
            )
            return result

        parsed = urlparse(endpoint)

        if parsed.scheme != "http":
            result["reason"] = (
                "POC validator permits local HTTP only"
            )
            return result

        if (
            parsed.username
            or parsed.password
            or parsed.fragment
        ):
            result["reason"] = "Invalid endpoint URL"
            return result

        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(
                    parsed.hostname,
                    parsed.port or 80,
                    type=socket.SOCK_STREAM,
                )
            }

            if not addresses or not all(
                ipaddress.ip_address(address).is_loopback
                for address in addresses
            ):
                result["reason"] = (
                    "Only loopback endpoints are permitted"
                )
                return result

            with httpx.Client(
                timeout=5.0,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response = client.get(endpoint)

            result["http_status"] = response.status_code
            result["reachable"] = True

            if response.status_code == 200:
                result["status"] = "connected"
                result["reason"] = "HTTP health check succeeded"
            else:
                result["status"] = "error"
                result["reason"] = (
                    "Health check returned non-200 response"
                )

        except Exception as exc:
            result["status"] = "error"
            result["reason"] = (
                f"Connection failed: {type(exc).__name__}"
            )

        return result
