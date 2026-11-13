"""HEAAP Phase 19.6 - External agent test planning integration."""

from app.services.external_agent_approval_gate import (
    load_onboarding_review,
)
from app.services.dynamic_external_test_planner import (
    generate_dynamic_test_plan,
    save_dynamic_test_plan,
)


def prepare_external_agent_test_plan(review_file, output_dir=None):
    review = load_onboarding_review(review_file)

    agent = review.get("agent")
    discovered = review.get("discovered_endpoint")

    if not isinstance(agent, dict):
        raise ValueError("Missing reviewed agent details")

    if not isinstance(discovered, dict):
        raise ValueError("Missing discovered endpoint details")

    if agent.get("manifest_valid") is not True:
        raise PermissionError("Invalid agent manifest")

    if discovered.get("provider") != "databricks":
        raise PermissionError("Unsupported endpoint provider")

    if discovered.get("endpoint_name") != agent.get("endpoint_name"):
        raise PermissionError("Endpoint identity mismatch")

    if review.get("review_status") not in {
        "pending_manual_review",
        "approved",
    }:
        raise PermissionError("Review is not eligible for planning")

    manifest = {
        "agent_id": agent.get("agent_id"),
        "endpoint_name": agent.get("endpoint_name"),
        "capabilities": agent.get("declared_capabilities"),
    }

    plan = generate_dynamic_test_plan(manifest)

    plan["source_review_id"] = review.get("review_id")
    plan["source_review_status"] = review.get("review_status")
    plan["capabilities_verified"] = (
        agent.get("capabilities_verified") is True
    )

    path = save_dynamic_test_plan(plan, output_dir)

    return {
        "plan": plan,
        "plan_file": path,
    }
