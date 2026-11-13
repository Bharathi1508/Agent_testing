
import asyncio

from app.services.functional_testing_engine import (
    FunctionalTestingEngine,
)

from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
)


# Execute an already-approved agent through
# the existing governance-controlled supervisor.
def approved_agent_test_executor(
    agent_id,
    capability,
    payload,
):
    response = execute_supervisor_request(
        capability=capability,
        payload=payload,
        preferred_agent_id=agent_id,
    )

    if response.get("status") != "success":
        raise RuntimeError(
            "Supervisor execution was not successful."
        )

    agent_result = response.get("result")

    if not isinstance(agent_result, dict):
        raise ValueError(
            "Agent response must be a dictionary."
        )

    if agent_result.get("status") != "success":
        raise RuntimeError(
            "Metadata Agent returned an unsuccessful status."
        )

    if agent_result.get("action") != capability:
        raise ValueError(
            "Metadata Agent returned the wrong action."
        )

    tables = agent_result.get("result")

    if not isinstance(tables, list):
        raise ValueError(
            "Expected a list of tables."
        )

    for table in tables:
        if not isinstance(table, dict):
            raise ValueError(
                "Each table must be a dictionary."
            )

        if not isinstance(table.get("table_name"), str):
            raise ValueError(
                "Missing or invalid table_name."
            )

        if not isinstance(table.get("table_type"), str):
            raise ValueError(
                "Missing or invalid table_type."
            )

    return agent_result


async def main():

    engine = FunctionalTestingEngine(
        agent_executor=approved_agent_test_executor
    )

    result = await engine.run_test(
        agent_id="metadata_agent_001",
        capability="list_tables",
        test_input={
            "action": "list_tables"
        },
        expected_keys=[
            "action",
            "result",
            "status",
        ],
    )

    print("\nHEAAP FUNCTIONAL TEST RESULT")
    print("----------------------------")
    print("Agent:", result.get("agent_id"))
    print("Capability:", result.get("capability"))
    print("Status:", result.get("status"))
    print("Passed:", result.get("passed"))
    print("Error:", result.get("error", "None"))
    print(
        "Execution Time:",
        result.get("execution_time_ms"),
        "ms",
    )

    if result.get("passed"):
        response = result.get("response", {})
        print(
            "Tables Retrieved:",
            len(response.get("result", [])),
        )


if __name__ == "__main__":
    asyncio.run(main())
