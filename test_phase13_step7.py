
"""
HEAAP - Phase 13, Step 7
Dynamic Functional Test Execution

Tests registered agents using generated
test cases and produces a test report.
"""

import json

from app.services.dynamic_test_runner import (
    run_dynamic_agent_tests,
)


def main():

    agent_id = "metadata_agent_001"

    print("\n====================================")
    print("HEAAP DYNAMIC FUNCTIONAL TESTING")
    print("====================================")

    # Step 1: Execute dynamically generated tests
    report = run_dynamic_agent_tests(agent_id)

    # Step 2: Display summary
    print("\nTEST SUMMARY")
    print("------------------------------------")

    print("Agent:", report.get("agent_id"))
    print("Overall Status:", report.get("status"))
    print("Overall Passed:", report.get("passed"))

    print("Total Tests:", report.get("total_tests", 0))
    print("Passed Tests:", report.get("passed_tests", 0))
    print("Failed Tests:", report.get("failed_tests", 0))
    print("Error Tests:", report.get("error_tests", 0))
    print("Blocked Tests:", report.get("blocked_tests", 0))

    print(
        "Unsupported Capabilities:",
        report.get("unsupported_capabilities", [])
    )

    # Step 3: Display individual test results
    print("\nDETAILED TEST RESULTS")
    print("------------------------------------")

    for result in report.get("results", []):

        print("\nTest ID:", result.get("test_id"))
        print("Agent:", result.get("agent_id"))
        print("Capability:", result.get("capability"))
        print("Status:", result.get("status"))
        print("Passed:", result.get("passed"))

        print(
            "Execution Time:",
            result.get("execution_time_ms"),
            "ms"
        )

        print("Errors:", result.get("errors", []))

    # Step 4: Display complete JSON report
    print("\nCOMPLETE JSON REPORT")
    print("------------------------------------")

    print(json.dumps(report, indent=4, default=str))


if __name__ == "__main__":
    main()
