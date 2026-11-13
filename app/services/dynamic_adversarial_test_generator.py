"""
HEAAP - Phase 15.3
Dynamic Adversarial Test Generator

Generates test cases from trusted capability schemas.
Does not execute agents or call external endpoints.
"""

from copy import deepcopy
from typing import Any

from app.registry.agent_registry import get_registered_agent
from app.registry.capability_schema_registry import get_capability_schema


def valid_value(field_name: str, definition: dict[str, Any]) -> Any:
    if "const" in definition:
        return definition["const"]

    field_type = definition.get("type")

    if field_type == "string":
        return "sample_value"
    if field_type == "integer":
        return 1
    if field_type == "number":
        return 1.5
    if field_type == "boolean":
        return True
    if field_type == "array":
        return []
    if field_type == "object":
        return {}

    raise ValueError(
        f"Unsupported schema type for field '{field_name}'"
    )


def invalid_value(field_type: str) -> Any:
    if field_type == "string":
        return 12345
    if field_type in ("integer", "number"):
        return "invalid_number"
    if field_type == "boolean":
        return "invalid_boolean"
    if field_type == "array":
        return "invalid_array"
    if field_type == "object":
        return "invalid_object"

    raise ValueError(f"Unsupported field type: {field_type}")


def generate_dynamic_adversarial_tests(
    agent_id: str,
) -> list[dict[str, Any]]:

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError(f"Agent '{agent_id}' is not registered")

    tests = []

    for capability in manifest.capabilities:

        schema = get_capability_schema(agent_id, capability)

        if schema is None:
            print(f"SKIPPED: No schema for {capability}")
            continue

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        if not isinstance(required, list) or not isinstance(properties, dict):
            raise ValueError(f"Invalid schema for {capability}")

        base_payload = {}

        for field_name in required:
            if field_name not in properties:
                raise ValueError(
                    f"Missing property definition: {field_name}"
                )

            base_payload[field_name] = valid_value(
                field_name,
                properties[field_name],
            )

        def add_case(scenario, payload):
            tests.append({
                "test_id": f"DYN_ADV_{len(tests) + 1:03d}",
                "agent_id": agent_id,
                "capability": capability,
                "scenario": scenario,
                "category": "input_validation",
                "input": deepcopy(payload),
                "expected_outcome": "rejected",
                "execution_mode": "generation_only",
            })

        for field_name in required:

            # Missing required field
            payload = deepcopy(base_payload)
            payload.pop(field_name)

            add_case(
                f"missing_{field_name}",
                payload,
            )

            definition = properties[field_name]
            field_type = definition.get("type")

            # Incorrect field type
            payload = deepcopy(base_payload)
            payload[field_name] = invalid_value(field_type)

            add_case(
                f"invalid_{field_name}_type",
                payload,
            )

            # Empty string where nonempty is required
            if (
                field_type == "string"
                and definition.get("minLength", 0) > 0
            ):
                payload = deepcopy(base_payload)
                payload[field_name] = ""

                add_case(
                    f"empty_{field_name}",
                    payload,
                )

    return tests
