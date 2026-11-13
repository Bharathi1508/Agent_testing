import os
from unittest.mock import patch

from app.adapters.databricks_agent_adapter import (
    DatabricksAgentAdapter,
    DatabricksAdapterError,
)
from app.adapters.real_agent_contract import AgentExecutionRequest


class TestManifest:
    agent_id = "databricks_test_agent_001"
    execution_type = "databricks"
    framework = "Databricks"
    status = "inactive"
    endpoint_name = "heaap-test-endpoint"
    capabilities = ["chat"]


def main():
    adapter = DatabricksAgentAdapter(dry_run=True)

    request = AgentExecutionRequest(
        agent_id="databricks_test_agent_001",
        capability="chat",
        test_id="PH17_DBX_001",
        payload={
            "messages": [
                {
                    "role": "user",
                    "content": "Test message",
                }
            ]
        },
    )

    env = {
        "HEAAP_ALLOWED_DATABRICKS_ENDPOINT": "heaap-test-endpoint",
        "HEAAP_APPROVED_AGENT_ID": "databricks_test_agent_001",
    }

    with patch.dict(os.environ, env):
        with patch(
            "app.adapters.databricks_agent_adapter.get_registered_agent",
            return_value=TestManifest(),
        ):
            with patch(
                "app.adapters.databricks_agent_adapter.requests.post"
            ) as post:

                result = adapter.execute(request)

                assert result.status == "not_executed"
                assert result.execution_target == "databricks_dry_run"
                post.assert_not_called()

                print("PASSED: Dry-run completed")
                print("PASSED: No HTTP request made")

                invalid_request = AgentExecutionRequest(
                    agent_id=request.agent_id,
                    capability="unknown_capability",
                    test_id="PH17_DBX_002",
                    payload=request.payload,
                )

                try:
                    adapter.execute(invalid_request)
                except DatabricksAdapterError:
                    print("PASSED: Unknown capability blocked")
                else:
                    raise AssertionError(
                        "Unknown capability was allowed"
                    )

                real_adapter = DatabricksAgentAdapter(dry_run=False)

                try:
                    real_adapter.execute(request)
                except DatabricksAdapterError:
                    print("PASSED: Inactive agent execution blocked")
                else:
                    raise AssertionError(
                        "Inactive agent was executed"
                    )

                post.assert_not_called()

    print("\nPHASE 17.4: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
