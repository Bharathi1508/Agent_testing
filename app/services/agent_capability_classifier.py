"""
HEAAP - Dynamic Agent Capability Classifier
Phase 22.5

Maps declared agent capabilities to suggested test suites.

This module does not execute, verify, register,
or approve discovered agents.
"""

from typing import Any


CAPABILITY_TEST_MAPPING = {
    "metadata_search": ["metadata_correctness"],
    "schema_discovery": ["schema_validation"],
    "column_description": ["column_description_validation"],
    "sql_generation": ["sql_generation_validation"],
    "sql_validation": ["sql_safety_validation"],
    "sql_execution": ["sql_execution_validation"],
    "fraud_detection": ["fraud_detection_evaluation"],
}


def classify_agent(candidate: dict[str, Any]) -> dict[str, Any]:
    """Classify an agent using its declared capabilities."""

    agent_id = candidate.get("agent_id")

    declared = candidate.get("capabilities", [])

    if not isinstance(declared, list):
        declared = []

    capabilities = sorted({
        capability.strip().lower()
        for capability in declared
        if isinstance(capability, str) and capability.strip()
    })

    suggested_suites = sorted({
        suite
        for capability in capabilities
        for suite in CAPABILITY_TEST_MAPPING.get(capability, [])
    })

    unmapped_capabilities = [
        capability
        for capability in capabilities
        if capability not in CAPABILITY_TEST_MAPPING
    ]

    if not capabilities:
        status = "requires_classification"
    elif unmapped_capabilities:
        status = "requires_classification"
    else:
        status = "pending_review"

    return {
        "agent_id": agent_id,
        "declared_capabilities": capabilities,
        "suggested_test_suites": suggested_suites,
        "unmapped_capabilities": unmapped_capabilities,
        "capabilities_verified": False,
        "classification_status": status,
        "production_approved": False,
    }
