"""
HEAAP Phase 15
Capability Input Schema Registry

Schemas describe input requirements.
They do not grant permission to execute an agent.
"""

from typing import Any


CAPABILITY_INPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "metadata_agent_001": {
        "list_tables": {
            "required": ["action"],
            "properties": {
                "action": {"type": "string", "const": "list_tables"}
            },
        },
        "get_columns": {
            "required": ["action", "table_name"],
            "properties": {
                "action": {"type": "string", "const": "get_columns"},
                "table_name": {"type": "string", "minLength": 1},
            },
        },
        "check_column": {
            "required": ["action", "table_name", "column_name"],
            "properties": {
                "action": {"type": "string", "const": "check_column"},
                "table_name": {"type": "string", "minLength": 1},
                "column_name": {"type": "string", "minLength": 1},
            },
        },
        "search_columns": {
            "required": ["action", "column_name"],
            "properties": {
                "action": {"type": "string", "const": "search_columns"},
                "column_name": {"type": "string", "minLength": 1},
            },
        },
    }
}


def get_capability_schema(
    agent_id: str,
    capability: str,
) -> dict[str, Any] | None:
    """
    Retrieve the declared schema for a capability.
    """

    agent_schemas = CAPABILITY_INPUT_SCHEMAS.get(agent_id, {})

    schema = agent_schemas.get(capability)

    if schema is None:
        return None

    # Return a copy to prevent callers from modifying
    # the shared schema registry.
    from copy import deepcopy

    return deepcopy(schema)


def list_agent_capability_schemas(
    agent_id: str,
) -> dict[str, Any]:
    """
    List all available schemas for an agent.
    """

    from copy import deepcopy

    return deepcopy(
        CAPABILITY_INPUT_SCHEMAS.get(agent_id, {})
    )
