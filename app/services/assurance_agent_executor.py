
"""
HEAAP - Phase 13
Assurance Agent Executor

Runs controlled functional tests for
registered inactive agents.

This executor is separate from the
production Dynamic Supervisor.

IMPORTANT:
- No automatic activation
- No governance approval changes
- No arbitrary endpoint execution
- Only explicitly configured test adapters
"""

from typing import Any, Callable

from app.registry.agent_registry import (
    get_registered_agent,
)


class AssuranceExecutionError(Exception):
    """Raised when assurance execution is denied or fails."""


# =====================================================
# TRUSTED LOCAL TEST ADAPTERS
# =====================================================

def test_metadata_agent(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute the Metadata Agent for testing.

    Only use this adapter with read-only,
    sandbox-scoped Databricks credentials.
    """

    from app.graphs.metadata_graph import graph

    result = graph.invoke(payload)

    if not isinstance(result, dict):
        raise AssuranceExecutionError(
            "Metadata Agent returned an invalid response."
        )

    return result


# =====================================================
# EXPLICIT ASSURANCE TEST ALLOWLIST
# =====================================================

ASSURANCE_TEST_HANDLERS: dict[
    str, Callable[[dict[str, Any]], dict[str, Any]]
] = {
    "metadata_agent_001": test_metadata_agent,
}

ASSURANCE_TEST_CAPABILITIES = {
    "metadata_agent_001": {
        "list_tables",
        "describe_table",
    },
}


# =====================================================
# ASSURANCE AGENT EXECUTOR
# =====================================================

class AssuranceAgentExecutor:

    def execute(
        self,
        agent_id: str,
        capability: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        # Step 1: Validate input
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise AssuranceExecutionError(
                "Valid agent_id is required."
            )

        if not isinstance(capability, str) or not capability.strip():
            raise AssuranceExecutionError(
                "Valid capability is required."
            )

        if not isinstance(payload, dict):
            raise AssuranceExecutionError(
                "Payload must be a dictionary."
            )

        # Step 2: Verify registered agent
        manifest = get_registered_agent(agent_id)

        if manifest is None:
            raise AssuranceExecutionError(
                "Agent is not registered."
            )

        # Step 3: Require inactive status
        if manifest.status != "inactive":
            raise AssuranceExecutionError(
                "Assurance executor accepts inactive agents only."
            )

        # Step 4: Verify execution type
        if manifest.execution_type != "local":
            raise AssuranceExecutionError(
                "Only local test adapters are supported."
            )

        # Step 5: Verify capability declaration
        declared_capabilities = {
            str(item).strip().lower()
            for item in manifest.capabilities
        }

        capability = capability.strip().lower()

        if capability not in declared_capabilities:
            raise AssuranceExecutionError(
                "Capability is not declared in the manifest."
            )

        # Step 6: Verify trusted test adapter
        handler = ASSURANCE_TEST_HANDLERS.get(agent_id)

        allowed = ASSURANCE_TEST_CAPABILITIES.get(
            agent_id, set()
        )

        if handler is None or capability not in allowed:
            raise AssuranceExecutionError(
                "Agent or capability is not allowlisted for testing."
            )

        # Step 7: Validate test payload
        if payload.get("action") != capability:
            raise AssuranceExecutionError(
                "Payload action must match the test capability."
            )

        if capability == "describe_table":
            if not isinstance(payload.get("table_name"), str):
                raise AssuranceExecutionError(
                    "describe_table requires table_name."
                )

        # Step 8: Execute trusted test adapter
        try:
            result = handler(payload.copy())

        except Exception as exc:
            raise AssuranceExecutionError(
                "Assurance agent execution failed."
            ) from exc

        return result


def execute_assurance_agent(
    agent_id: str,
    capability: str,
    payload: dict[str, Any],
) -> dict[str, Any]:

    executor = AssuranceAgentExecutor()

    return executor.execute(
        agent_id=agent_id,
        capability=capability,
        payload=payload,
    )
