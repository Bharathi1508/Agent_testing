from app.adapters.real_agent_contract import (
    AgentExecutionRequest,
)

from app.adapters.langgraph_agent_adapter import (
    LangGraphAgentAdapter,
)


def main():

    adapter = LangGraphAgentAdapter()

    scenarios = [
        (
            "missing_action",
            {},
            "rejected",
            "INVALID_INPUT",
        ),
        (
            "invalid_action_type",
            {
                "action": 12345,
            },
            "rejected",
            "INVALID_INPUT",
        ),
        (
            "missing_question",
            {
                "action": "generate_sql",
            },
            "rejected",
            "INVALID_INPUT",
        ),
        (
            "invalid_question_type",
            {
                "action": "generate_sql",
                "question": 12345,
            },
            "rejected",
            "INVALID_INPUT",
        ),
        (
            "valid_generate_sql",
            {
                "action": "generate_sql",
                "question": "Show total loans",
            },
            "success",
            None,
        ),
        (
            "valid_validate_sql",
            {
                "action": "validate_sql",
                "sql_query": "SELECT 1",
            },
            "success",
            None,
        ),
    ]

    for index, (
        name,
        payload,
        expected_status,
        expected_error,
    ) in enumerate(scenarios, start=1):

        capability = (
            payload.get("action")
            if payload.get("action") in (
                "generate_sql",
                "validate_sql",
            )
            else "generate_sql"
        )

        request = AgentExecutionRequest(
            agent_id="sql_agent_001",
            capability=capability,
            payload=payload,
            test_id=f"PH17_LG_{index:03d}",
        )

        result = adapter.execute(request)

        assert result.status == expected_status, (
            f"{name}: unexpected status {result.status}"
        )

        assert result.error_code == expected_error, (
            f"{name}: unexpected error {result.error_code}"
        )

        print(
            f"PASSED: {name} "
            f"| {result.status} "
            f"| {result.error_code}"
        )

    print("\nPHASE 17.3: ALL 6 LANGGRAPH CHECKS PASSED")


if __name__ == "__main__":
    main()
