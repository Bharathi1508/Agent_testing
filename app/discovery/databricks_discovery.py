
"""
HEAAP - Phase 10
Databricks Agent Discovery Service

Discovers Databricks serving endpoints and identifies
trusted agent candidates for onboarding.

Discovery does NOT approve, register, or execute agents.
"""

import logging
import os
import re
from typing import Any
from urllib.parse import urlparse
import truststore

truststore.inject_into_ssl()
import requests
from dotenv import load_dotenv

from app.discovery.discovery_models import (
    DiscoveredAgent,
    DiscoveryResult,
)

load_dotenv()

logger = logging.getLogger(__name__)


class DatabricksDiscoveryError(Exception):
    """Raised when Databricks discovery fails."""


class DatabricksAgentDiscovery:

    def __init__(self):

        self.host = (
            os.getenv("DATABRICKS_HOST")
            or os.getenv("DATABRICKS_SERVER_HOSTNAME")
            or ""
        ).strip().rstrip("/")

        self.token = (
            os.getenv("DATABRICKS_TOKEN") or ""
        ).strip()

        self.timeout = int(
            os.getenv("DATABRICKS_DISCOVERY_TIMEOUT", "20")
        )

        self.allowed_endpoints = {
            value.strip()
            for value in os.getenv(
                "DATABRICKS_AGENT_ENDPOINT_ALLOWLIST", ""
            ).split(",")
            if value.strip()
        }

        self.capability_map = self._parse_capability_map(
            os.getenv("DATABRICKS_AGENT_CAPABILITY_MAP", "")
        )

        if not self.host:
            raise DatabricksDiscoveryError(
                "DATABRICKS_HOST is not configured"
            )

        if "://" not in self.host:
            self.host = f"https://{self.host}"

        parsed = urlparse(self.host)

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in ("", "/")
        ):
            raise DatabricksDiscoveryError(
                "DATABRICKS_HOST must be an HTTPS workspace URL"
            )

        if not self.token:
            raise DatabricksDiscoveryError(
                "DATABRICKS_TOKEN is not configured"
            )

        if self.timeout <= 0:
            raise DatabricksDiscoveryError(
                "Discovery timeout must be positive"
            )

        self.verify_ssl = self._get_ssl_verification()

    @staticmethod
    def _get_ssl_verification():
        """
        Use a configured CA bundle if available.

        Otherwise use Requests' default certificate verification.
        Never disable TLS verification.
        """

        ca_bundle = (
            os.getenv("DATABRICKS_CA_BUNDLE")
            or os.getenv("REQUESTS_CA_BUNDLE")
        )

        if ca_bundle:
            if not os.path.isfile(ca_bundle):
                raise DatabricksDiscoveryError(
                    "Configured CA certificate bundle does not exist"
                )
            return ca_bundle

        return True

    @staticmethod
    def _parse_capability_map(
        raw_value: str
    ) -> dict[str, list[str]]:

        result = {}

        for entry in raw_value.split(";"):

            entry = entry.strip()

            if not entry or "=" not in entry:
                continue

            endpoint_name, raw_capabilities = entry.split("=", 1)

            endpoint_name = endpoint_name.strip()

            capabilities = list(dict.fromkeys(
                capability.strip().lower()
                for capability in raw_capabilities.split("|")
                if capability.strip()
            ))

            if endpoint_name and capabilities:
                result[endpoint_name] = capabilities

        return result

    def _headers(self) -> dict[str, str]:

        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    @staticmethod
    def _safe_agent_id(endpoint_name: str) -> str:

        normalized = re.sub(
            r"[^A-Za-z0-9_-]",
            "_",
            endpoint_name
        )

        return f"dbx_{normalized}"

    @staticmethod
    def _raise_api_error(response: requests.Response):
        """
        Explain HTTP failures without printing credentials.
        """

        status = response.status_code

        error_code = None
        error_message = None

        try:
            body = response.json()

            if isinstance(body, dict):
                error_code = body.get("error_code")
                error_message = body.get("message")

        except ValueError:
            pass

        if status == 401:
            raise DatabricksDiscoveryError(
                "Databricks returned HTTP 401. "
                "Check the token and workspace configuration."
            )

        if status == 403:
            details = (
                f" Databricks error code: {error_code}."
                if error_code else ""
            )

            raise DatabricksDiscoveryError(
                "Databricks returned HTTP 403 Forbidden. "
                "The configured identity cannot list serving "
                "endpoints. Check endpoint permissions, "
                "workspace policies, and token identity."
                + details
            )

        if status >= 400:
            safe_code = (
                str(error_code)[:100]
                if error_code else "unknown"
            )

            raise DatabricksDiscoveryError(
                f"Databricks API returned HTTP {status}. "
                f"Error code: {safe_code}"
            )

    def list_serving_endpoints(
        self
    ) -> list[dict[str, Any]]:
        """
        GET /api/2.0/serving-endpoints
        """

        url = (
            f"{self.host}/api/2.0/serving-endpoints"
        )

        try:
            response = requests.get(
                url,
                headers=self._headers(),
                timeout=self.timeout,
                verify=self.verify_ssl,
                allow_redirects=False,
            )

        except requests.exceptions.SSLError as exc:

            raise DatabricksDiscoveryError(
                "SSL certificate verification failed. "
                "Configure your organization's trusted CA "
                "bundle or Windows certificate trust."
            ) from exc

        except requests.exceptions.RequestException as exc:

            logger.error(
                "Databricks discovery connection failed: %s",
                type(exc).__name__
            )

            raise DatabricksDiscoveryError(
                "Unable to connect to Databricks serving API"
            ) from exc

        self._raise_api_error(response)

        try:
            data = response.json()

        except ValueError as exc:
            raise DatabricksDiscoveryError(
                "Databricks returned an invalid JSON response"
            ) from exc

        if not isinstance(data, dict):
            raise DatabricksDiscoveryError(
                "Unexpected Databricks API response"
            )

        endpoints = data.get("endpoints", [])

        if not isinstance(endpoints, list):
            raise DatabricksDiscoveryError(
                "Databricks endpoint list is invalid"
            )

        return endpoints

    def discover_agents(self) -> DiscoveryResult:
        """
        Return allowlisted endpoints with verified,
        explicitly configured capabilities.
        """

        endpoints = self.list_serving_endpoints()

        discovered = []
        errors = []

        for endpoint in endpoints:

            if not isinstance(endpoint, dict):
                continue

            endpoint_name = endpoint.get("name")

            if not isinstance(endpoint_name, str):
                continue

            if endpoint_name not in self.allowed_endpoints:
                continue

            capabilities = self.capability_map.get(
                endpoint_name, []
            )

            if not capabilities:
                errors.append(
                    f"Endpoint '{endpoint_name}' has no "
                    "trusted capability mapping"
                )
                continue

            try:
                agent = DiscoveredAgent(
                    agent_id=self._safe_agent_id(
                        endpoint_name
                    ),
                    agent_name=endpoint_name,
                    provider="databricks",
                    execution_type="databricks",
                    endpoint_name=endpoint_name,
                    capabilities=capabilities,
                    description=(
                        "Databricks serving endpoint "
                        "discovered by HEAAP"
                    ),
                    metadata={
                        "source": "databricks_serving_api",
                        "endpoint_state": endpoint.get(
                            "state", {}
                        ),
                    },
                )

                discovered.append(agent)

            except Exception as exc:
                logger.warning(
                    "Invalid discovery candidate %s: %s",
                    endpoint_name,
                    type(exc).__name__
                )

                errors.append(
                    f"Could not validate endpoint "
                    f"'{endpoint_name}'"
                )

        return DiscoveryResult(
            provider="databricks",
            discovered_count=len(discovered),
            agents=discovered,
            errors=errors,
        )


def discover_databricks_agents() -> DiscoveryResult:

    discovery = DatabricksAgentDiscovery()

    return discovery.discover_agents()
