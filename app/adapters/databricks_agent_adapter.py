
"""
HEAAP Phase 17.4
Databricks Agent Execution Adapter

Features:
- Registry-based agent validation
- Capability verification
- Endpoint allowlisting
- Workspace host allowlisting
- Dry-run mode (default)
- Explicit real-execution controls
- Chat-completions request format
- Structured execution results

Does not automatically activate agents.
Does not execute generated SQL directly.
"""

import os
import re
from copy import deepcopy
from urllib.parse import quote, urlsplit

import requests

from app.adapters.real_agent_contract import (
    AgentExecutionRequest,
    AgentExecutionResult,
    RealAgentAdapter,
)

from app.registry.agent_registry import (
    get_registered_agent,
)


ENDPOINT_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class DatabricksAdapterError(Exception):
    """Raised when Databricks agent execution is not permitted or fails."""
    pass


class DatabricksAgentAdapter(RealAgentAdapter):

    def __init__(self, *, dry_run=True):
        self.dry_run = dry_run

    def _prepare(self, request: AgentExecutionRequest):

        # STEP 1: Retrieve registered agent
        manifest = get_registered_agent(request.agent_id)

        if manifest is None:
            raise DatabricksAdapterError(
                "Agent is not registered"
            )

        # STEP 2: Validate execution type
        if manifest.execution_type != "databricks":
            raise DatabricksAdapterError(
                "Agent is not registered as Databricks"
            )

        # STEP 3: Validate agent status
        # Inactive agents may be inspected in dry-run mode.
        # Real execution requires active status.
        if not self.dry_run and manifest.status != "active":
            raise DatabricksAdapterError(
                "Agent must be active for real execution"
            )

        # STEP 4: Validate registered capability
        if request.capability not in manifest.capabilities:
            raise DatabricksAdapterError(
                "Capability is not registered"
            )

        # STEP 5: Validate endpoint name
        endpoint = manifest.endpoint_name

        if (
            not isinstance(endpoint, str)
            or not ENDPOINT_PATTERN.fullmatch(endpoint)
        ):
            raise DatabricksAdapterError(
                "Invalid serving endpoint name"
            )

        # STEP 6: Validate endpoint allowlist
        allowed_endpoint = os.getenv(
            "HEAAP_ALLOWED_DATABRICKS_ENDPOINT", ""
        )

        if endpoint != allowed_endpoint:
            raise DatabricksAdapterError(
                "Endpoint is not allowlisted"
            )

        # STEP 7: Validate approved agent ID
        approved_agent = os.getenv(
            "HEAAP_APPROVED_AGENT_ID", ""
        )

        if request.agent_id != approved_agent:
            raise DatabricksAdapterError(
                "Agent is not approved for this execution"
            )

        # STEP 8: Validate payload
        if not isinstance(request.payload, dict):
            raise DatabricksAdapterError(
                "Payload must be a dictionary"
            )

        messages = request.payload.get("messages")

        if not isinstance(messages, list) or not messages:
            raise DatabricksAdapterError(
                "Expected a non-empty messages list"
            )

        for message in messages:

            if not isinstance(message, dict):
                raise DatabricksAdapterError(
                    "Invalid message object"
                )

            if message.get("role") not in (
                "system",
                "user",
                "assistant",
            ):
                raise DatabricksAdapterError(
                    "Unsupported message role"
                )

            if (
                not isinstance(message.get("content"), str)
                or not message["content"]
            ):
                raise DatabricksAdapterError(
                    "Message content must be non-empty text"
                )

        # Restrict to the fields supported by this adapter.
        return endpoint, {
            "messages": deepcopy(messages)
        }

    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResult:

        endpoint, payload = self._prepare(request)

        # STEP 9: Dry-run mode
        # No Databricks network request is performed.
        if self.dry_run:

            return AgentExecutionResult(
                agent_id=request.agent_id,
                capability=request.capability,
                test_id=request.test_id,
                status="not_executed",
                response={
                    "status": "not_executed",
                    "reason": "Dry-run mode",
                    "endpoint": endpoint,
                    "request_format": "chat_completions",
                },
                error_code=None,
                execution_target="databricks_dry_run",
            )

        # STEP 10: Explicit execution switch
        if os.getenv(
            "HEAAP_ENABLE_DATABRICKS_EXECUTION"
        ) != "true":
            raise DatabricksAdapterError(
                "Real Databricks execution is disabled"
            )

        # STEP 11: Load workspace configuration
        host = os.getenv(
            "DATABRICKS_HOST", ""
        ).rstrip("/")

        token = os.getenv(
            "DATABRICKS_TOKEN", ""
        )

        parsed = urlsplit(host)

        # STEP 12: Validate workspace URL
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise DatabricksAdapterError(
                "DATABRICKS_HOST must be an HTTPS workspace origin"
            )

        # STEP 13: Validate workspace allowlist
        allowed_host = os.getenv(
            "HEAAP_ALLOWED_DATABRICKS_HOST", ""
        ).rstrip("/")

        if not allowed_host or host != allowed_host:
            raise DatabricksAdapterError(
                "Workspace host is not allowlisted"
            )

        # STEP 14: Validate authentication
        if not token:
            raise DatabricksAdapterError(
                "DATABRICKS_TOKEN is missing"
            )

        # STEP 15: Construct Databricks endpoint URL
        url = (
            f"{host}/serving-endpoints/"
            f"{quote(endpoint, safe='')}/invocations"
        )

        # STEP 16: Invoke approved Databricks endpoint
        try:

            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=(5, 30),
                allow_redirects=False,
            )

            response.raise_for_status()

            data = response.json()

        except requests.RequestException as exc:
            raise DatabricksAdapterError(
                "Databricks request failed: "
                f"{type(exc).__name__}"
            ) from exc

        except ValueError as exc:
            raise DatabricksAdapterError(
                "Databricks returned invalid JSON"
            ) from exc

        # STEP 17: Validate response structure
        if not isinstance(data, dict):
            raise DatabricksAdapterError(
                "Unexpected Databricks response structure"
            )

        # STEP 18: Normalize execution result
        # HTTP success does not mean assurance passed.
        return AgentExecutionResult(
            agent_id=request.agent_id,
            capability=request.capability,
            test_id=request.test_id,
            status="response_received",
            response=data,
            error_code=None,
            execution_target="databricks_serving",
        )
