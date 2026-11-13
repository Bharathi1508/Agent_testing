"""
HEAAP Phase 16.4
Framework-aware execution adapter.

Only explicitly approved mock execution is supported.
"""

from copy import deepcopy
from typing import Any

from app.registry.agent_registry import get_registered_agent
from app.adapters.mock_sql_agent import MockSQLAgent


class AdapterExecutionError(Exception):
    pass


class AgentExecutionAdapter:

    MOCK_AGENT_ID = "sql_agent_001"

    def execute(
        self,
        agent_id: str,
        payload: dict[str, Any],
        *,
        approved_test: bool = False,
    ) -> dict[str, Any]:

        if approved_test is not True:
            raise AdapterExecutionError(
                "Explicit test approval is required"
            )

        if agent_id != self.MOCK_AGENT_ID:
            raise AdapterExecutionError(
                "Agent is not approved for mock execution"
            )

        manifest = get_registered_agent(agent_id)

        if manifest is None:
            raise AdapterExecutionError(
                "Agent is not registered"
            )

        if manifest.execution_type != "local":
            raise AdapterExecutionError(
                "Only local mock execution is supported"
            )

        if manifest.status != "inactive":
            raise AdapterExecutionError(
                "Mock onboarding tests require an inactive agent"
            )

        if not isinstance(payload, dict):
            raise AdapterExecutionError(
                "Payload must be a dictionary"
            )

        action = payload.get("action")

        # Invalid action values are allowed through to
        # the mock agent so its input validation can be tested.
        if isinstance(action, str):
            if action not in manifest.capabilities:
                raise AdapterExecutionError(
                    "Action is not a registered capability"
                )

        mock_agent = MockSQLAgent()

        return mock_agent.execute(deepcopy(payload))


def execute_approved_mock_test(
    agent_id: str,
    payload: dict[str, Any],
    *,
    approved_test: bool = False,
) -> dict[str, Any]:

    adapter = AgentExecutionAdapter()

    return adapter.execute(
        agent_id,
        payload,
        approved_test=approved_test,
    )
