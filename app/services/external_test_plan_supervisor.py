"""HEAAP Phase 19.7 - External test plan supervisor review."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.external_agent_approval_gate import (
    load_onboarding_review,
)
from app.services.external_test_plan_validator import (
    validate_external_test_plan,
)


def supervise_external_test_plan(plan, review):
    validation = validate_external_test_plan(plan)
    reasons = list(validation["errors"])

    if not isinstance(review, dict):
        reasons.append("Invalid onboarding review")
        review = {}

    agent = review.get("agent")

    if not isinstance(agent, dict):
        reasons.append("Missing reviewed agent")
        agent = {}

    if plan.get("agent_id") != agent.get("agent_id"):
        reasons.append("Agent identity mismatch")

    if plan.get("source_review_id") != review.get("review_id"):
        reasons.append("Source review ID mismatch")

    if plan.get("source_review_status") != review.get("review_status"):
        reasons.append("Source review status mismatch")

    if plan.get("declared_capabilities") != agent.get(
        "declared_capabilities"
    ):
        reasons.append("Declared capabilities mismatch")

    if agent.get("manifest_valid") is not True:
        reasons.append("Manifest is not valid")

    if review.get("review_status") != "approved":
        reasons.append("Agent onboarding is not approved")

    if review.get("execution_authorized") is not True:
        reasons.append("Agent execution is not authorized")

    if agent.get("capabilities_verified") is not True:
        reasons.append("Agent capabilities are not verified")

    if agent.get("trust_status") != "verified":
        reasons.append("Agent trust is not verified")

    plan_valid = validation["valid"]

    onboarding_eligible = (
        review.get("review_status") == "approved"
        and review.get("execution_authorized") is True
        and agent.get("capabilities_verified") is True
        and agent.get("trust_status") == "verified"
        and agent.get("manifest_valid") is True
    )

    ready_for_separate_run_approval = (
        plan_valid
        and onboarding_eligible
        and len(reasons) == 0
    )

    return {
        "decision_id": uuid.uuid4().hex,
        "phase": "19.7",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agent_id": plan.get("agent_id"),
        "plan_id": plan.get("plan_id"),
        "source_review_id": review.get("review_id"),
        "plan_valid": plan_valid,
        "validated_tests": validation["validated_tests"],
        "ready_for_separate_run_approval": (
            ready_for_separate_run_approval
        ),
        "decision": (
            "ready_for_run_approval"
            if ready_for_separate_run_approval
            else "blocked"
        ),
        "reasons": reasons,
        "execution_authorized_by_supervisor": False,
        "live_endpoint_invoked": False,
        "production_approved": False,
    }


def review_external_test_plan_file(
    plan_file,
    review_file,
    output_dir=None,
):
    with Path(plan_file).open("r", encoding="utf-8") as file:
        plan = json.load(file)

    review = load_onboarding_review(review_file)

    decision = supervise_external_test_plan(plan, review)

    if output_dir is None:
        output_dir = Path("reports/phase19_7_supervisor")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    decision_file = output_dir / (
        decision["decision_id"] + ".json"
    )

    with decision_file.open("x", encoding="utf-8") as file:
        json.dump(decision, file, indent=2)

    return {
        "decision": decision,
        "decision_file": str(decision_file),
    }
