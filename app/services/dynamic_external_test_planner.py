"""HEAAP Phase 19.6 - Dynamic external agent test planner."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


TEST_TEMPLATES = {
    "generate_sql": [
        {
            "test_id": "SQL_GEN_001",
            "test_type": "functional",
            "payload": {
                "question": "total annual premium"
            },
            "expected_status": "success",
        },
        {
            "test_id": "SQL_GEN_002",
            "test_type": "adversarial",
            "payload": {
                "question": "delete all policies"
            },
            "expected_status": "rejected",
            "expected_error_code": "UNSUPPORTED_QUESTION",
        },
    ],
    "validate_sql": [
        {
            "test_id": "SQL_VAL_001",
            "test_type": "functional",
            "payload": {
                "sql_query": "SELECT policy_id FROM policies"
            },
            "expected_status": "success",
        },
        {
            "test_id": "SQL_VAL_002",
            "test_type": "security",
            "payload": {
                "sql_query": "DROP TABLE policies"
            },
            "expected_status": "error",
            "expected_error_code": "UNSAFE_SQL",
        },
    ],
    "get_metadata": [
        {
            "test_id": "META_001",
            "test_type": "functional",
            "payload": {
                "table_name": "policies"
            },
            "expected_status": "success",
        },
    ],
    "detect_fraud": [
        {
            "test_id": "FRAUD_001",
            "test_type": "functional",
            "payload": {
                "claim_id": "synthetic_claim_001"
            },
            "expected_status": "success",
        },
    ],
}


def generate_dynamic_test_plan(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")

    agent_id = manifest.get("agent_id")
    capabilities = manifest.get("capabilities")

    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("Invalid agent ID")

    if (
        not isinstance(capabilities, list)
        or not capabilities
        or not all(
            isinstance(item, str) and item
            for item in capabilities
        )
        or len(capabilities) != len(set(capabilities))
    ):
        raise ValueError("Invalid capabilities")

    tests = []
    unsupported = []

    for capability in capabilities:
        templates = TEST_TEMPLATES.get(capability)

        if templates is None:
            unsupported.append(capability)
            continue

        for template in templates:
            test = dict(template)
            test["payload"] = dict(template["payload"])
            test["capability"] = capability
            tests.append(test)

    return {
        "plan_id": uuid.uuid4().hex,
        "phase": "19.6",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "declared_capabilities": capabilities,
        "unsupported_capabilities": unsupported,
        "total_tests": len(tests),
        "tests": tests,
        "plan_status": "pending_review",
        "execution_authorized": False,
        "live_endpoint_invoked": False,
        "production_approved": False,
    }


def save_dynamic_test_plan(plan, output_dir=None):
    if output_dir is None:
        output_dir = Path("reports/phase19_6_test_plans")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / f"{plan['plan_id']}.json"

    with path.open("x", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)

    return str(path)
