
"""
HEAAP - Phase 14, Step 2
Security Test Runner Verification
"""

import json

from app.services.security_test_runner import (
    run_security_agent_tests,
)


def main():

    print("\nHEAAP SECURITY TEST RUNNER", flush=True)
    print("====================================")

    agent_id = "metadata_agent_001"

    print("Agent:", agent_id, flush=True)
    print("Executing security tests...", flush=True)

    report = run_security_agent_tests(agent_id)

    print("\nSECURITY TEST SUMMARY")
    print("------------------------------------")
    print("Overall Status:", report["status"])
    print("Overall Passed:", report["passed"])
    print("Total Tests:", report["total_tests"])
    print("Passed Tests:", report["passed_tests"])
    print("Failed Tests:", report["failed_tests"])
    print("Error Tests:", report["error_tests"])
    print(
        "Inconclusive Tests:",
        report["inconclusive_tests"]
    )

    print("\nINDIVIDUAL TEST RESULTS")
    print("------------------------------------")

    for result in report["results"]:

        print("\nTest ID:", result["test_id"])
        print("Status:", result["status"])
        print("Passed:", result["passed"])
        print("Observation:", result["observation"])

    print("\nCOMPLETE JSON REPORT")
    print("------------------------------------")

    print(
        json.dumps(report, indent=4),
        flush=True,
    )


if __name__ == "__main__":
    main()
