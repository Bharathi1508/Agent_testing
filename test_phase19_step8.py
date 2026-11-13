"""HEAAP Phase 19.8 - LangGraph supervisor tests."""

import copy
import tempfile

from pathlib import Path

from app.services.dynamic_external_test_planner import (
    generate_dynamic_test_plan,
)

from app.services.external_agent_approval_gate import (
    load_onboarding_review,
)

from app.services.phase19_langgraph_supervisor import (
    run_langgraph_supervisor,
    save_supervisor_report,
)


REVIEW_FILE = (
    "reports/phase18_9_onboarding/"
    "ccccc93e0f114d618a46a865bc5dd76c.json"
)


def main():
    print("HEAAP PHASE 19.8 - LANGGRAPH SUPERVISOR")
    print("=" * 55)

    review = load_onboarding_review(REVIEW_FILE)

    agent = review["agent"]

    plan = generate_dynamic_test_plan({
        "agent_id": agent["agent_id"],
        "capabilities": agent["declared_capabilities"],
    })

    plan["source_review_id"] = review["review_id"]
    plan["source_review_status"] = review["review_status"]

    report = run_langgraph_supervisor(plan, review)

    assert report["plan_validation"]["valid"] is True

    print("LangGraph test plan validation: PASS")

    assert (
        report["supervisor_decision"]["decision"]
        == "blocked"
    )

    print("Pending onboarding review blocked: PASS")

    expected_trace = [
        "validate_test_plan",
        "review_agent_approval",
        "supervisor_decision",
        "generate_supervisor_report",
    ]

    assert report["workflow_trace"] == expected_trace

    print("LangGraph workflow trace: PASS")

    # Simulated approved review; does not modify real records.
    approved_review = copy.deepcopy(review)

    approved_review["review_status"] = "approved"
    approved_review["execution_authorized"] = True
    approved_review["agent"]["capabilities_verified"] = True
    approved_review["agent"]["trust_status"] = "verified"

    approved_plan = copy.deepcopy(plan)
    approved_plan["source_review_status"] = "approved"

    approved_report = run_langgraph_supervisor(
        approved_plan,
        approved_review,
    )

    assert (
        approved_report["supervisor_decision"]["decision"]
        == "ready_for_run_approval"
    )

    assert (
        approved_report["governance"]["execution_authorized"]
        is False
    )

    print("Synthetic approved review evaluated: PASS")

    # Invalid plans must always be blocked.
    invalid_plan = copy.deepcopy(approved_plan)
    invalid_plan["execution_authorized"] = True

    invalid_report = run_langgraph_supervisor(
        invalid_plan,
        approved_review,
    )

    assert (
        invalid_report["supervisor_decision"]["decision"]
        == "blocked"
    )

    print("Invalid plan blocked: PASS")

    with tempfile.TemporaryDirectory() as temp_dir:
        report_file = save_supervisor_report(
            report,
            output_dir=Path(temp_dir),
        )

        assert Path(report_file).is_file()

        print("Supervisor report saved: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 19.8: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
