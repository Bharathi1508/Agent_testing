
import json

from app.services.test_case_generator import (
    generate_agent_test_cases,
    TestCaseGenerator,
)


def main():
    agent_id = "metadata_agent_001"

    print("\nHEAAP DYNAMIC TEST CASE GENERATOR")
    print("================================")

    result = generate_agent_test_cases(agent_id)

    print("Agent:", result.get("agent_id"))
    print("Status:", result.get("status"))
    print("Tests Generated:", result.get("test_count"))
    print(
        "Unsupported Capabilities:",
        result.get("unsupported_capabilities", [])
    )

    print("\nGenerated Test Cases:")

    for case in result.get("test_cases", []):
        print(json.dumps(case, indent=2))

    generator = TestCaseGenerator()

    capability_result = generator.generate_for_capability(
        agent_id=agent_id,
        capability="list_tables"
    )

    print("\nIndividual Capability Test")
    print("Capability Status:", capability_result.get("status"))
    print("Test Count:", capability_result.get("test_count", 0))


if __name__ == "__main__":
    main()
