"""
HEAAP - Phase 16.3
Automatic Adversarial Test Generator

Generates negative tests from registered capability schemas.
No agent execution, network calls, or agent activation.
"""

from copy import deepcopy
from typing import Any

from app.registry.agent_registry import get_registered_agent
from app.registry.dynamic_capability_registry import (
    get_dynamic_capability_schemas,
)


MAX_TESTS_PER_AGENT = 100


def valid_value(
    field_name: str,
    definition: dict[str, Any],
) -> Any:

    if "const" in definition:
        return deepcopy(definition["const"])

    field_type = definition["type"]

    if field_type == "string":
        return "x" * max(1, definition.get("minLength", 0))

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
        f"Unsupported field type for {field_name}"
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


def generate_agent_adversarial_tests(
    agent_id: str,
) -> list[dict[str, Any]]:

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError(
            f"Agent '{agent_id}' is not registered"
        )

    schemas = get_dynamic_capability_schemas(agent_id)

    if not schemas:
        raise ValueError(
            f"No capability schemas registered for '{agent_id}'"
        )

    if set(schemas) != set(manifest.capabilities):
        raise ValueError(
            "Capability schemas do not match agent manifest"
        )

    tests = []

    for capability in sorted(schemas):

        schema = schemas[capability]
        required = schema["required"]
        properties = schema["properties"]

        base_payload = {}

        for field_name in required:
            base_payload[field_name] = valid_value(
                field_name,
                properties[field_name],
            )

        def add_test(scenario, payload, field_name):

            if len(tests) >= MAX_TESTS_PER_AGENT:
                raise ValueError(
                    "Maximum generated test count exceeded"
                )

            tests.append({
                "test_id": f"AUTO_ADV_{len(tests) + 1:03d}",
                "agent_id": agent_id,
                "capability": capability,
                "scenario": scenario,
                "field_under_test": field_name,
                "category": "input_validation",
                "input": deepcopy(payload),
                "expected_outcome": "rejected",
                "expected_error_category": "input_validation",
                "execution_mode": "generation_only",
                "schema_source": "dynamic_capability_registry",
            })

        for field_name in required:

            definition = properties[field_name]
            field_type = definition["type"]

            # Test 1: Required field missing
            payload = deepcopy(base_payload)
            payload.pop(field_name)

            add_test(
                f"missing_{field_name}",
                payload,
                field_name,
            )

            # Test 2: Incorrect field type
            payload = deepcopy(base_payload)
            payload[field_name] = invalid_value(
                field_type
            )

            add_test(
                f"invalid_{field_name}_type",
                payload,
                field_name,
            )

            # Test 3: Empty string
            if (
                field_type == "string"
                and definition.get("minLength", 0) > 0
            ):

                payload = deepcopy(base_payload)
                payload[field_name] = ""

                add_test(
                    f"empty_{field_name}",
                    payload,
                    field_name,
                )

    return tests
