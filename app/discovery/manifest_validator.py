
"""
HEAAP - Phase 10
Manifest Validator

Validates newly discovered agents before registration.

This module:
- Validates identity and capability declarations
- Validates provider and execution configuration
- Enforces endpoint allowlists
- Prevents unsafe automatic activation
- Returns structured validation results

It does NOT register, approve, or execute agents.
"""

import os
import re
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError

from app.discovery.discovery_models import DiscoveredAgent


class ManifestValidationResult(BaseModel):
    agent_id: str = ""
    valid: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    normalized_manifest: dict[str, Any] | None = None


class AgentManifestValidator:
    """
    Validate agent discovery records against
    HEAAP onboarding requirements.
    """

    ALLOWED_PROVIDERS = {
        "databricks",
        "langgraph",
        "external",
    }

    ALLOWED_EXECUTION_TYPES = {
        "local",
        "databricks",
        "rest",
    }

    PROVIDER_EXECUTION_MAP = {
        "databricks": {"databricks"},
        "langgraph": {"local"},
        "external": {"rest"},
    }

    AGENT_ID_PATTERN = re.compile(
        r"^[A-Za-z0-9_-]{1,128}$"
    )

    CAPABILITY_PATTERN = re.compile(
        r"^[a-z][a-z0-9_]{0,127}$"
    )

    def __init__(self):

        self.allowed_databricks_endpoints = {
            value.strip()
            for value in os.getenv(
                "DATABRICKS_AGENT_ENDPOINT_ALLOWLIST",
                ""
            ).split(",")
            if value.strip()
        }

        self.allowed_rest_hosts = {
            value.strip().lower()
            for value in os.getenv(
                "HEAAP_REST_AGENT_HOST_ALLOWLIST",
                ""
            ).split(",")
            if value.strip()
        }

        self.allowed_local_agents = {
            value.strip()
            for value in os.getenv(
                "HEAAP_LOCAL_AGENT_ALLOWLIST",
                ""
            ).split(",")
            if value.strip()
        }

    def validate(
        self,
        candidate: DiscoveredAgent | dict[str, Any]
    ) -> ManifestValidationResult:

        errors = []
        warnings = []

        try:
            if isinstance(candidate, dict):
                agent = DiscoveredAgent.model_validate(
                    candidate
                )
            elif isinstance(candidate, DiscoveredAgent):
                agent = candidate
            else:
                return ManifestValidationResult(
                    errors=[
                        "Candidate must be a DiscoveredAgent "
                        "or dictionary"
                    ]
                )

        except ValidationError as exc:

            return ManifestValidationResult(
                agent_id=(
                    str(candidate.get("agent_id", ""))
                    if isinstance(candidate, dict)
                    else ""
                ),
                errors=[
                    f"{'.'.join(map(str, error['loc']))}: "
                    f"{error['msg']}"
                    for error in exc.errors()
                ],
            )

        # 1. Agent identity
        if not self.AGENT_ID_PATTERN.fullmatch(
            agent.agent_id
        ):
            errors.append(
                "Agent ID contains invalid characters"
            )

        if not agent.agent_name.strip():
            errors.append(
                "Agent name cannot be empty"
            )

        # 2. Provider and execution compatibility
        if agent.provider not in self.ALLOWED_PROVIDERS:
            errors.append(
                "Unsupported agent provider"
            )

        if (
            agent.execution_type
            not in self.ALLOWED_EXECUTION_TYPES
        ):
            errors.append(
                "Unsupported execution type"
            )

        expected_types = self.PROVIDER_EXECUTION_MAP.get(
            agent.provider, set()
        )

        if agent.execution_type not in expected_types:
            errors.append(
                "Provider and execution type do not match"
            )

        # 3. Capabilities
        if not agent.capabilities:
            errors.append(
                "Agent must declare at least one capability"
            )

        for capability in agent.capabilities:

            if not self.CAPABILITY_PATTERN.fullmatch(
                capability
            ):
                errors.append(
                    f"Invalid capability: {capability}"
                )

        # 4. Databricks execution
        if agent.execution_type == "databricks":

            if not agent.endpoint_name:
                errors.append(
                    "Databricks endpoint_name is required"
                )

            elif (
                agent.endpoint_name
                not in self.allowed_databricks_endpoints
            ):
                errors.append(
                    "Databricks endpoint is not allowlisted"
                )

        # 5. REST execution
        if agent.execution_type == "rest":

            if not agent.endpoint_url:
                errors.append(
                    "REST endpoint_url is required"
                )

            else:
                parsed = urlparse(agent.endpoint_url)

                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.fragment
                ):
                    errors.append(
                        "REST endpoint must be a valid HTTPS URL"
                    )

                elif (
                    parsed.hostname.lower()
                    not in self.allowed_rest_hosts
                ):
                    errors.append(
                        "REST endpoint host is not allowlisted"
                    )

        # 6. Local execution
        if agent.execution_type == "local":

            if (
                agent.agent_id
                not in self.allowed_local_agents
            ):
                errors.append(
                    "Local agent is not allowlisted"
                )

        # 7. Version and metadata
        if not re.fullmatch(
            r"\d+\.\d+\.\d+",
            agent.version
        ):
            warnings.append(
                "Version is not in MAJOR.MINOR.PATCH format"
            )

        if not agent.description.strip():
            warnings.append(
                "Agent description is missing"
            )

        # 8. Do not trust a candidate's claimed status
        normalized = agent.model_dump(
            mode="json"
        )

        normalized["status"] = "inactive"
        normalized["approved"] = False

        if errors:
            return ManifestValidationResult(
                agent_id=agent.agent_id,
                valid=False,
                errors=errors,
                warnings=warnings,
                normalized_manifest=None,
            )

        return ManifestValidationResult(
            agent_id=agent.agent_id,
            valid=True,
            errors=[],
            warnings=warnings,
            normalized_manifest=normalized,
        )


def validate_discovered_agent(
    candidate: DiscoveredAgent | dict[str, Any]
) -> ManifestValidationResult:
    """
    Convenience function for the onboarding service.
    """

    validator = AgentManifestValidator()

    return validator.validate(candidate)
