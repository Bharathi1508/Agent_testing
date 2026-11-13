
"""
HEAAP - Phase 14, Step 5
Adversarial Test Runner Verification
"""

import json

from app.services.adversarial_test_runner import (
    run_adversarial_agent_tests,
)


def main():

    print("\nHEAAP ADVERSARIAL TEST RUNNER")
    print("=" * 45)

    report = run_adversarial_agent_tests(
        "metadata_agent_001"
    )

    print("\nEXECUTION SUMMARY")
    print("-" * 45)

    print("Agent:", report["agent_id"])
    print("Status:", report["status"])
    print("Total:", report["total_tests"])
    print("Passed:", report["passed_tests"])
    print("Failed:", report["failed_tests"])
    print("Errors:", report["error_tests"])
    print(
        "Inconclusive:",
        report["inconclusive_tests"]
    )

    print("\nCOMPLETE JSON REPORT")
    print("-" * 45)

    print(
        json.dumps(
            report,
            indent=4
        )
    )


if __name__ == "__main__":
    main()

