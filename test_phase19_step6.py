"""HEAAP Phase 19.6 - Dynamic agent test planning tests."""

import tempfile
from pathlib import Path

from app.services.dynamic_external_test_planner import (
    generate_dynamic_test_plan,
)
from app.services.external_agent_test_planning_service import (
    prepare_external_agent_test_plan,
)


REVIEW_FILE = (
    "reports/phase18_9_onboarding/"
    "ccccc93e0f114d618a46a865bc5dd76c.json"
)


def main():
    print("HEAAP PHASE 19.6 - DYNAMIC TEST PLANNING")
    print("=" * 55)

    with tempfile.TemporaryDirectory() as temp_dir:
        result = prepare_external_agent_test_plan(
            REVIEW_FILE,
            output_dir=Path(temp_dir),
        )

        plan = result["plan"]

        assert plan["agent_id"] == "external_sql_agent_001"
        print("External SQL Agent identified: PASS")

        assert plan["declared_capabilities"] == [
            "generate_sql",
            "validate_sql",
        ]
        print("Declared capabilities identified: PASS")

        assert plan["total_tests"] == 4
        print("Four SQL assurance tests generated: PASS")

        assert plan["source_review_status"] == (
            "pending_manual_review"
        )
        print("Pending onboarding review preserved: PASS")

        assert plan["execution_authorized"] is False
        assert plan["live_endpoint_invoked"] is False
        print("Unauthorized execution prevented: PASS")

        assert Path(result["plan_file"]).is_file()
        print("Test plan JSON saved: PASS")

    # Unknown capabilities must not be treated as verified.
    unknown = generate_dynamic_test_plan({
        "agent_id": "unknown_agent_001",
        "capabilities": ["unknown_capability"],
    })

    assert unknown["total_tests"] == 0
    assert unknown["unsupported_capabilities"] == [
        "unknown_capability"
    ]

    print("Unknown capability handled safely: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 19.6: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
