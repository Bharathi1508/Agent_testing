
"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Phase 14 - Step 5
Adversarial Test Runner Verification

Purpose:
    Execute generated adversarial tests for
    a registered agent and display the results.

Input:
    Registered agent ID

Output:
    Complete adversarial assurance report
"""

import json
import sys

from app.services.adversarial_test_runner import (
    run_adversarial_agent_tests,
)


def main():

    agent_id = "metadata_agent_001"

    print("\n" + "=" * 55)
    print("HEAAP - ADVERSARIAL TEST RUNNER")
    print("=" * 55)

    print(f"\nTesting Agent: {agent_id}")

    try:
        report = run_adversarial_agent_tests(
            agent_id
        )

    except Exception as exc:

        print("\nTEST EXECUTION FAILED")
        print(
            f"Error Type: {type(exc).__name__}"
        )
        print(f"Error Message: {exc}")

        sys.exit(1)

    print("\nEXECUTION SUMMARY")
    print("-" * 55)

    print(
        "Agent:",
        report.get("agent_id")
    )

    print(
        "Status:",
        report.get("status")
    )

    print(
        "Total Tests:",
        report.get("total_tests")
    )

    print(
        "Passed Tests:",
        report.get("passed_tests")
    )

    print(
        "Failed Tests:",
        report.get("failed_tests")
    )

    print(
        "Error Tests:",
        report.get("error_tests")
    )

    print(
        "Inconclusive Tests:",
        report.get("inconclusive_tests")
    )

    print("\nCOMPLETE JSON REPORT")
    print("-" * 55)

    print(
        json.dumps(
            report,
            indent=4,
            default=str
        )
    )


if __name__ == "__main__":
    main()
