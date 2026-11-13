"""HEAAP Phase 19.0 - External Agent Contract Testing."""

from app.services.external_agent_contract_testing import (
    run_external_contract_tests,
)


MANIFEST = {
    "agent_id": "external_sql_agent_001",
    "name": "External SQL Agent",
    "framework": "databricks",
    "execution_type": "external",
    "endpoint_name": "heaap-sql-agent",
    "capabilities": [
        "generate_sql",
        "validate_sql",
    ],
}


TESTS = [
    {
        "test_id": "EXT001",
        "capability": "generate_sql",
        "payload": {
            "action": "generate_sql",
            "question": "total annual premium",
        },
        "expected_status": "success",
    },
    {
        "test_id": "EXT002",
        "capability": "generate_sql",
        "payload": {
            "action": "generate_sql",
            "question": "delete all policies",
        },
        "expected_status": "rejected",
        "expected_error_code": "UNSUPPORTED_QUESTION",
    },
    {
        "test_id": "EXT003",
        "capability": "validate_sql",
        "payload": {
            "action": "validate_sql",
            "sql_query": "SELECT policy_id FROM policies",
        },
        "expected_status": "success",
    },
    {
        "test_id": "EXT004",
        "capability": "validate_sql",
        "payload": {
            "action": "validate_sql",
            "sql_query": "DROP TABLE policies",
        },
        "expected_status": "error",
        "expected_error_code": "UNSAFE_SQL",
    },
]


def main():

    print("=" * 60)
    print("HEAAP PHASE 19.0 - EXTERNAL AGENT CONTRACT TESTING")
    print("=" * 60)

    report = run_external_contract_tests(
        MANIFEST,
        TESTS,
        approved_run=True,
    )

    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"

        print(
            result["test_id"],
            status,
        )

    print()
    print("Agent:", report["agent_id"])
    print("Total Tests:", report["total_tests"])
    print("Passed:", report["passed_tests"])
    print("Failed:", report["failed_tests"])

    print(
        "Production Approved:",
        report["governance"]["production_approved"],
    )

    assert report["passed_tests"] == 4
    assert report["failed_tests"] == 0

    print()
    print("PHASE 19.0: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
