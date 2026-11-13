
from app.adapters.real_agent_contract import AgentExecutionRequest
from app.adapters.real_sql_agent_adapter import RealSQLAgentAdapter

AGENT_ID = "sql_agent_real_001"
adapter = RealSQLAgentAdapter()


def execute(capability, payload, test_id):
    request = AgentExecutionRequest(
        agent_id=AGENT_ID,
        capability=capability,
        payload=payload,
        test_id=test_id,
    )
    return adapter.execute(request)


def check(name, result, expected_status, expected_error=None):
    passed = result.status == expected_status

    if expected_error is not None:
        passed = passed and result.error_code == expected_error

    print(
        ("PASS" if passed else "FAIL"),
        name,
        "| status:", result.status,
        "| error:", result.error_code,
    )
    return passed


results = []

# T001: Valid SQL generation
# Replace this question with an exact supported question
# from app/agents/real_sql_agent.py if necessary.
results.append(check(
    "Valid SQL generation",
    execute(
        "generate_sql",
        {
            "action": "generate_sql",
            "question": "total annual premium",
        },
        "T001",
    ),
    "success",
))

# T002: Empty question
results.append(check(
    "Empty question",
    execute(
        "generate_sql",
        {"action": "generate_sql", "question": ""},
        "T002",
    ),
    "error",
    "INVALID_INPUT",
))

# T003: Missing question
results.append(check(
    "Missing question",
    execute(
        "generate_sql",
        {"action": "generate_sql"},
        "T003",
    ),
    "error",
    "INVALID_INPUT",
))

# T004: Wrong question type
results.append(check(
    "Wrong question type",
    execute(
        "generate_sql",
        {"action": "generate_sql", "question": 123},
        "T004",
    ),
    "error",
    "INVALID_INPUT",
))

# T005: Valid SELECT screening
results.append(check(
    "Valid SELECT screening",
    execute(
        "validate_sql",
        {
            "action": "validate_sql",
            "sql_query": "SELECT policy_id FROM policies",
        },
        "T005",
    ),
    "success",
))

# T006: DROP statement rejection
results.append(check(
    "DROP statement rejection",
    execute(
        "validate_sql",
        {
            "action": "validate_sql",
            "sql_query": "DROP TABLE policies",
        },
        "T006",
    ),
    "error",
    "UNSAFE_SQL",
))

# T007: Multiple statement rejection
results.append(check(
    "Multiple statement rejection",
    execute(
        "validate_sql",
        {
            "action": "validate_sql",
            "sql_query": "SELECT * FROM policies; DROP TABLE policies",
        },
        "T007",
    ),
    "error",
    "UNSAFE_SQL",
))

# T008: Missing SQL
results.append(check(
    "Missing SQL",
    execute(
        "validate_sql",
        {"action": "validate_sql"},
        "T008",
    ),
    "error",
    "INVALID_INPUT",
))

# T009: Wrong action
results.append(check(
    "Wrong action",
    execute(
        "generate_sql",
        {
            "action": "validate_sql",
            "question": "Show policies",
        },
        "T009",
    ),
    "error",
    "INVALID_INPUT",
))

# T010: Unsupported capability
results.append(check(
    "Unsupported capability",
    execute(
        "delete_database",
        {"action": "delete_database"},
        "T010",
    ),
    "error",
    "UNSUPPORTED_CAPABILITY",
))

passed = sum(results)
total = len(results)

print()
print("=" * 55)
print("PHASE 18.3 ADAPTER TEST SUMMARY")
print("=" * 55)
print("Passed:", passed)
print("Total:", total)
print("Failed:", total - passed)

if passed != total:
    raise SystemExit("PHASE 18.3: TESTS FAILED")

print("PHASE 18.3: ALL TESTS PASSED")
