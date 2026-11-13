"""HEAAP Phase 20.2 - Automatic candidate onboarding."""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.dynamic_external_test_planner import (
    TEST_TEMPLATES,
    generate_dynamic_test_plan,
)


SUPPORTED_PROVIDERS = {
    "databricks",
    "langgraph",
    "custom_rest",
}

SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


def validate_discovery_metadata(discovery):
    if not isinstance(discovery, dict):
        raise ValueError("Discovery metadata must be an object")

    provider = discovery.get("provider")
    endpoint_name = discovery.get("endpoint_name")
    agent_id = discovery.get("agent_id")
    capabilities = discovery.get("declared_capabilities")

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError("Unsupported provider")

    if (
        not isinstance(agent_id, str)
        or not SAFE_IDENTIFIER.fullmatch(agent_id)
    ):
        raise ValueError("Invalid agent ID")

    if (
        not isinstance(endpoint_name, str)
        or not SAFE_IDENTIFIER.fullmatch(endpoint_name)
    ):
        raise ValueError("Invalid endpoint name")

    if (
        not isinstance(capabilities, list)
        or not capabilities
        or not all(
            isinstance(c, str)
            and SAFE_IDENTIFIER.fullmatch(c)
            for c in capabilities
        )
        or len(capabilities) != len(set(capabilities))
    ):
        raise ValueError("Invalid declared capabilities")

    return {
        "provider": provider,
        "agent_id": agent_id,
        "endpoint_name": endpoint_name,
        "declared_capabilities": list(capabilities),
    }


def build_candidate_manifest(discovery):
    normalized = validate_discovery_metadata(discovery)

    return {
        "agent_id": normalized["agent_id"],
        "name": normalized["agent_id"],
        "framework": normalized["provider"],
        "execution_type": "external",
        "endpoint_name": normalized["endpoint_name"],
        "capabilities": normalized["declared_capabilities"],
    }


def map_agent_capabilities(manifest):
    capabilities = manifest["capabilities"]

    supported = [
        capability
        for capability in capabilities
        if capability in TEST_TEMPLATES
    ]

    unsupported = [
        capability
        for capability in capabilities
        if capability not in TEST_TEMPLATES
    ]

    return {
        "supported_capabilities": supported,
        "unsupported_capabilities": unsupported,
        "test_templates_available": {
            capability: len(TEST_TEMPLATES[capability])
            for capability in supported
        },
    }


def create_pending_onboarding_review(discovery, output_dir=None):
    normalized = validate_discovery_metadata(discovery)
    manifest = build_candidate_manifest(normalized)
    mapping = map_agent_capabilities(manifest)

    plan = generate_dynamic_test_plan(manifest)

    review_id = uuid.uuid4().hex

    review = {
        "review_id": review_id,
        "phase": "20.2",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "agent": {
            "agent_id": manifest["agent_id"],
            "name": manifest["name"],
            "framework": manifest["framework"],
            "execution_type": "external",
            "endpoint_name": manifest["endpoint_name"],
            "declared_capabilities": manifest["capabilities"],
            "manifest_valid": True,
            "capabilities_verified": False,
            "trust_status": "unverified",
            "production_approved": False,
        },
        "discovered_endpoint": {
            "provider": normalized["provider"],
            "endpoint_name": normalized["endpoint_name"],
        },
        "capability_mapping": mapping,
        "planned_test_count": plan["total_tests"],
        "review_status": "pending_manual_review",
        "execution_authorized": False,
        "automatically_registered": False,
        "production_approved": False,
    }

    if output_dir is None:
        output_dir = Path("reports/phase20_2")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    review_file = output_dir / f"{review_id}.json"
    manifest_file = output_dir / f"{review_id}_manifest.json"
    plan_file = output_dir / f"{review_id}_plan.json"

    artifacts = [
        (review_file, review),
        (manifest_file, manifest),
        (plan_file, plan),
    ]

    for path, content in artifacts:
        with path.open("x", encoding="utf-8") as file:
            json.dump(content, file, indent=2)

    return {
        "review": review,
        "manifest": manifest,
        "test_plan": plan,
        "review_file": str(review_file),
        "manifest_file": str(manifest_file),
        "plan_file": str(plan_file),
    }
