"""HEAAP Phase 19.7 - Supervisor test plan validation."""

import copy
import json
import tempfile
from pathlib import Path

from app.services.dynamic_external_test_planner import (
    generate_dynamic_test_plan,
)
from app.services.external_agent_approval_gate import (
    load_onboarding_review,
)
from app.services.external_test_plan_validator import (
    validate_external_test_plan,
)
from app.services.external_test_plan_supervisor import (
    supervise_external_test_plan,
    review_external_test_plan_file,
)


REVIEW_FILE = (
    "reports/phase18_9_onboarding/"
    "ccccc93e0f114d618a46a865bc5dd76c.json"
)


def main():
    print("HEAAP PHASE 19.7 - SUPERVISOR TEST PLAN REVIEW")
    print("=" * 55)

    review = load_onboarding_review(REVIEW_FILE)
    agent = review["agent"]

    manifest = {
        "agent_id": agent["agent_id"],
        "capabilities": agent["declared_capabilities"],
    }

    plan = generate_dynamic_test_plan(manifest)
    plan["source_review_id"] = review["review_id"]
    plan["source_review_status"] = review["review_status"]

    validation = validate_external_test_plan(plan)

    assert validation["valid"] is True
    assert validation["validated_tests"] == 4

    print("Valid SQL test plan: PASS")

    decision = supervise_external_test_plan(plan, review)

    assert decision["decision"] == "blocked"
    assert decision["plan_valid"] is True
    assert decision["ready_for_separate_run_approval"] is False
    assert decision["execution_authorized_by_supervisor"] is False

    print("Pending agent blocked by supervisor: PASS")

    # Detect an unauthorized test payload.
    modified = copy.deepcopy(plan)
    modified["tests"][0]["payload"]["question"] = (
        "DROP TABLE policies"
    )

    assert not validate_external_test_plan(modified)["valid"]

    print("Tampered test payload rejected: PASS")

    # Detect duplicate test IDs.
    duplicate = copy.deepcopy(plan)
    duplicate["tests"][1]["test_id"] = (
        duplicate["tests"][0]["test_id"]
    )

    assert not validate_external_test_plan(duplicate)["valid"]

    print("Duplicate test IDs rejected: PASS")

    # Detect an attempt to authorize execution via the plan.
    unauthorized = copy.deepcopy(plan)
    unauthorized["execution_authorized"] = True

    assert not validate_external_test_plan(unauthorized)["valid"]

    print("Plan-level authorization escalation blocked: PASS")

    # Test handling of an unknown capability.
    unknown = generate_dynamic_test_plan({
        "agent_id": "unknown_agent_001",
        "capabilities": ["unknown_capability"],
    })

    unknown_result = validate_external_test_plan(unknown)

    assert unknown_result["valid"] is True
    assert unknown_result["validated_tests"] == 0

    print("Unknown capability safely excluded: PASS")

    # Verify that the decision is saved to JSON.
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        plan_file = root / "test_plan.json"

        plan_file.write_text(
            json.dumps(plan, indent=2),
            encoding="utf-8",
        )

        result = review_external_test_plan_file(
            plan_file,
            REVIEW_FILE,
            output_dir=root / "decisions",
        )

        assert Path(result["decision_file"]).is_file()
        assert result["decision"]["decision"] == "blocked"

        print("Supervisor decision JSON saved: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 19.7: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
