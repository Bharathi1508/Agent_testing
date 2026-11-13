"""
HEAAP Phase 17.5 verification.

Uses the existing LangGraph SQL demonstration agent.
Does not invoke Databricks.
"""

import json
from pathlib import Path

from app.services.unified_adversarial_runner import (
    run_unified_tests,
    save_unified_report,
)


def main():

    agent_id = "sql_agent_001"

    test_file = Path(
        "generated_tests/sql_agent_001_adversarial_tests.json"
    )

    if not test_file.exists():
        raise FileNotFoundError(
            f"Generated test suite missing: {test_file}"
        )

    tests = json.loads(
        test_file.read_text(encoding="utf-8-sig")
    )

    print("HEAAP PHASE 17.5")
    print("=" * 50)
    print("Agent:", agent_id)
    print("Execution mode: langgraph_demo")
    print("Loaded tests:", len(tests))
    print()

    report = run_unified_tests(
        agent_id=agent_id,
        tests=tests,
        execution_mode="langgraph_demo",
        approved_run=True,
    )

    path = save_unified_report(report)

    print("\nPHASE 17.5 EXECUTION SUMMARY")
    print("=" * 50)

    for key in (
        "agent_id",
        "execution_mode",
        "status",
        "total_tests",
        "passed_tests",
        "failed_tests",
        "error_tests",
        "inconclusive_tests",
        "not_executed_tests",
        "production_approved",
    ):
        print(f"{key}: {report[key]}")

    print("\nReport saved to:", path)

    assert report["total_tests"] == 10
    assert report["passed_tests"] == 10
    assert report["failed_tests"] == 0
    assert report["error_tests"] == 0
    assert report["inconclusive_tests"] == 0

    print("\nPHASE 17.5: ALL 10 TESTS PASSED")


if __name__ == "__main__":
    main()
