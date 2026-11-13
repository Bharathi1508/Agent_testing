from app.adapters.real_agent_contract import (
    AgentExecutionRequest,
)
from app.adapters.local_metadata_adapter import (
    LocalMetadataAdapter,
)


def main():

    adapter = LocalMetadataAdapter()

    request = AgentExecutionRequest(
        agent_id="metadata_agent_001",
        capability="get_columns",
        test_id="PH17_REAL_001",
        payload={
            "action": "get_columns"
        },
    )

    result = adapter.execute(request)

    print("\nHEAAP PHASE 17 REAL AGENT RESULT")
    print("=" * 50)
    print("Agent:", result.agent_id)
    print("Capability:", result.capability)
    print("Execution target:", result.execution_target)
    print("Status:", result.status)
    print("Error code:", result.error_code)
    print("Response:", result.response)

    assert result.status == "rejected"
    assert result.error_code == "INVALID_INPUT"

    print("\nPHASE 17.2: REAL METADATA AGENT TEST PASSED")


if __name__ == "__main__":
    main()
