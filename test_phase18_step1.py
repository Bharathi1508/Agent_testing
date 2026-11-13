"""
HEAAP Phase 18.1 tests.
No database connection or network execution.
"""

from app.agents.real_sql_agent import run_sql_agent


def main():

    print("=" * 55)
    print("HEAAP PHASE 18.1 - REAL SQL AGENT")
    print("=" * 55)

    tests = [
        {
            "name": "Total premium",
            "question": "total annual premium",
            "expected": "success",
        },
        {
            "name": "Policy count",
            "question": "total number of policies",
            "expected": "success",
        },
        {
            "name": "Claim count",
            "question": "total number of claims",
            "expected": "success",
        },
        {
            "name": "Unknown question",
            "question": "show all secret customer records",
            "expected": "rejected",
        },
        {
            "name": "SQL injection attempt",
            "question": "total annual premium; DROP TABLE policies",
            "expected": "rejected",
        },
        {
            "name": "Empty question",
            "question": "",
            "expected": "rejected",
        },
        {
            "name": "Wrong input type",
            "question": 12345,
            "expected": "rejected",
        },
    ]

    passed = 0

    for index, test in enumerate(tests, start=1):

        result = run_sql_agent(test["question"])

        assert result["status"] == test["expected"], (
            f"Unexpected status for {test['name']}: {result}"
        )

        assert result["database_executed"] is False

        if test["expected"] == "success":
            assert result["validation_passed"] is True
            assert result["sql_query"].startswith("SELECT ")
        else:
            assert result["validation_passed"] is False
            assert result["sql_query"] == ""

        passed += 1

        print(
            f"TEST {index:02d} | "
            f"{test['name']} | PASSED"
        )

    print()
    print("Total tests:", len(tests))
    print("Passed:", passed)
    print("Failed:", len(tests) - passed)
    print("Database executed: False")
    print()
    print("PHASE 18.1: ALL TESTS PASSED")


if __name__ == "__main__":
    main()
