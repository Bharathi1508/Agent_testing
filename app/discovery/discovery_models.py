
"""
HEAAP - Phase 10
Discovered Agent Data Models

Represents agent candidates discovered from
Databricks, LangGraph, or external providers.

Discovery does not authorize execution.
"""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
)


class DiscoveredAgent(BaseModel):
    """
    Candidate agent returned by a trusted
    discovery adapter.
    """

    model_config = ConfigDict(
        extra="forbid"
    )

    agent_id: str = Field(
        min_length=1,
        max_length=128
    )

    agent_name: str = Field(
        min_length=1
    )

    provider: Literal[
        "databricks",
        "langgraph",
        "external"
    ]

    execution_type: Literal[
        "local",
        "databricks",
        "rest"
    ]

    endpoint_name: str | None = None

    endpoint_url: str | None = None

    capabilities: list[str] = Field(
        default_factory=list
    )

    description: str = ""

    version: str = "1.0.0"

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, value: str):
        """
        Restrict IDs to safe registry filenames.
        """

        import re

        if not re.fullmatch(
            r"[A-Za-z0-9_-]+",
            value
        ):
            raise ValueError(
                "Agent ID must contain only letters, "
                "numbers, underscores or hyphens"
            )

        return value

    @field_validator("capabilities")
    @classmethod
    def normalize_capabilities(
        cls,
        values: list[str]
    ):
        """
        Normalize and deduplicate capabilities.
        """

        normalized = []

        for value in values:

            capability = value.strip().lower()

            if not capability:
                continue

            if capability not in normalized:
                normalized.append(capability)

        return normalized


class DiscoveryResult(BaseModel):
    """
    Result of one discovery operation.
    """

    provider: str

    discovered_count: int = 0

    agents: list[DiscoveredAgent] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )


class OnboardingResult(BaseModel):
    """
    Result of registering a discovered agent.
    """

    agent_id: str

    status: Literal[
        "registered",
        "already_registered",
        "quarantined",
        "failed"
    ]

    registry_status: str = "inactive"

    message: str = ""
