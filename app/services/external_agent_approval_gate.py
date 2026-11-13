"""HEAAP Phase 19.1 - External Agent Approval Gate."""

import json
from pathlib import Path

from app.services.external_agent_contract_testing import (
    run_external_contract_tests,
)


def load_onboarding_review(review_file):

    path = Path(review_file).resolve()
    review_dir = Path("reports/phase18_9_onboarding").resolve()

    if review_dir not in path.parents or path.suffix != ".json":
        raise PermissionError("Invalid onboarding review path")

    if not path.is_file():
        raise FileNotFoundError("Onboarding review not found")

    with path.open("r", encoding="utf-8") as file:
        review = json.load(file)

    if not isinstance(review, dict):
        raise ValueError("Invalid onboarding review format")

    return review


def validate_onboarding_approval(review, manifest):

    if not isinstance(review, dict):
        raise ValueError("Review must be an object")

    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")

    agent = review.get("agent")

    if not isinstance(agent, dict):
        raise PermissionError("Missing reviewed agent details")

    if agent.get("agent_id") != manifest.get("agent_id"):
        raise PermissionError("Agent identity mismatch")

    if agent.get("endpoint_name") != manifest.get("endpoint_name"):
        raise PermissionError("Endpoint identity mismatch")

    discovered = review.get("discovered_endpoint")

    if not isinstance(discovered, dict):
        raise PermissionError("Missing discovered endpoint")

    if discovered.get("provider") != "databricks":
        raise PermissionError("Unexpected endpoint provider")

    if discovered.get("endpoint_name") != agent.get("endpoint_name"):
        raise PermissionError("Discovered endpoint mismatch")

    reviewed_capabilities = agent.get("declared_capabilities")
    manifest_capabilities = manifest.get("capabilities")

    if (
        not isinstance(reviewed_capabilities, list)
        or not isinstance(manifest_capabilities, list)
        or not reviewed_capabilities
        or not all(isinstance(x, str) for x in reviewed_capabilities)
        or not all(isinstance(x, str) for x in manifest_capabilities)
        or len(reviewed_capabilities) != len(set(reviewed_capabilities))
        or len(manifest_capabilities) != len(set(manifest_capabilities))
        or set(reviewed_capabilities) != set(manifest_capabilities)
    ):
        raise PermissionError("Capability mismatch")

    if agent.get("manifest_valid") is not True:
        raise PermissionError("Manifest validation failed")

    if review.get("review_status") != "approved":
        raise PermissionError("Manual onboarding approval required")

    if review.get("execution_authorized") is not True:
        raise PermissionError("Execution is not authorized")

    if agent.get("capabilities_verified") is not True:
        raise PermissionError("Capabilities not verified")

    if agent.get("trust_status") != "verified":
        raise PermissionError("Agent trust status not verified")

    return True


def run_approved_external_tests(
    review_file,
    manifest,
    tests,
    *,
    approved_run=False,
):

    if approved_run is not True:
        raise PermissionError("Explicit test approval required")

    review = load_onboarding_review(review_file)

    validate_onboarding_approval(review, manifest)

    return run_external_contract_tests(
        manifest,
        tests,
        approved_run=True,
    )
