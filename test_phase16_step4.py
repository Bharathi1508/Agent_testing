"""
HEAAP Phase 16.4
Execution Adapter Verification
"""

from app.adapters.agent_execution_adapter import (
    execute_approved_mock_test,
    AdapterExecutionError,
)


def check(name, condition):
    if not condition:
        raise AssertionError(f"FAILED: {name}")
    print(f"PASSED: {name}")


def main():

    agent_id = "sql_agent_001"

    # Test 1: Missing approval must be blocked.
    try:
        execute_approved_mock_test(
            agent_id,
            {
                "action": "generate_sql",
                "question": "Show total loans",
            },
        )
    except AdapterExecutionError:
        print("PASSED: Unapproved execution blocked")
    else:
        raise AssertionError(
            "Unapproved execution was not blocked"
        )

    # Test 2: Valid generate_sql mock request.
    response = execute_approved_mock_test(
        agent_id,
        {
            "action": "generate_sql",
            "question": "Show total loans",
        },
        approved_test=True,
    )

    check(
        "Valid mock SQL generation",
        response["status"] == "success"
        and response["result"]["mock"] is True,
    )

    # Test 3: Missing question.
    response = execute_approved_mock_test(
        agent_id,
        {
            "action": "generate_sql",
        },
        approved_test=True,
    )

    check(
        "Missing question rejected",
        response["status"] == "rejected"
        and response["error_code"] == "INVALID_INPUT",
    )

    # Test 4: Invalid question type.
    response = execute_approved_mock_test(
        agent_id,
        {
            "action": "generate_sql",
            "question": 12345,
        },
        approved_test=True,
    )

    check(
        "Invalid question type rejected",
        response["status"] == "rejected"
        and response["error_code"] == "INVALID_INPUT",
    )

    # Test 5: Valid SQL validation mock request.
    response = execute_approved_mock_test(
        agent_id,
        {
            "action": "validate_sql",
            "sql_query": "SELECT 1",
        },
        approved_test=True,
    )

    check(
        "Valid mock SQL validation",
        response["status"] == "success"
        and response["result"]["mock"] is True,
    )

    # Test 6: Missing SQL query.
    response = execute_approved_mock_test(
        agent_id,
        {
            "action": "validate_sql",
        },
        approved_test=True,
    )

    check(
        "Missing SQL query rejected",
        response["status"] == "rejected"
        and response["error_code"] == "INVALID_INPUT",
    )

    # Test 7: Unknown agent blocked.
    try:
        execute_approved_mock_test(
            "unknown_agent",
            {"action": "generate_sql"},
            approved_test=True,
        )
    except AdapterExecutionError:
        print("PASSED: Unknown agent blocked")
    else:
        raise AssertionError(
            "Unknown agent was not blocked"
        )

    print("\nPHASE 16.4: ALL 7 CHECKS PASSED")


if __name__ == "__main__":
    main()
