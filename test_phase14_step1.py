
"""
HEAAP - Phase 14, Step 1
Security Test Case Generation
"""

import json

from app.services.security_test_case_generator import (
    generate_security_test_cases,
)


def main():

    agent_id = "metadata_agent_001"

    print("\nHEAAP SECURITY TEST GENERATOR")
    print("================================")

    report = generate_security_test_cases(
        agent_id
    )

    print("\nGENERATION SUMMARY")
    print("--------------------------------")

    print("Agent:", report["agent_id"])
    print("Status:", report["status"])
    print("Total Security Tests:", report["test_count"])

    print("\nGENERATED TEST CASES")
    print("--------------------------------")

    for test_case in report["test_cases"]:

        print("\nTest ID:", test_case["test_id"])
        print("Name:", test_case["name"])
        print("Category:", test_case["category"])
        print(
            "Expected Outcome:",
            test_case["expected_outcome"]
        )

    print("\nCOMPLETE JSON")
    print("--------------------------------")

    print(
        json.dumps(
            report,
            indent=4
        )
    )


if __name__ == "__main__":
    main()
