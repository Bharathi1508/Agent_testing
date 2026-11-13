"""
HEAAP Phase 16.2
Persistent Capability Schema Registry

Registration does not execute or activate an agent.
"""

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.registry.agent_registry import get_registered_agent


SCHEMA_DIR = Path(__file__).resolve().parents[2] / "capability_schemas"
MAX_SCHEMA_BYTES = 65536
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")

SUPPORTED_TYPES = {
    "string", "integer", "number",
    "boolean", "array", "object"
}


def validate_schema_definition(schema: dict[str, Any]) -> None:
    if not isinstance(schema, dict):
        raise ValueError("Schema must be a JSON object")

    if set(schema) != {"required", "properties"}:
        raise ValueError(
            "Schema must contain only 'required' and 'properties'"
        )

    required = schema["required"]
    properties = schema["properties"]

    if not isinstance(required, list) or not isinstance(properties, dict):
        raise ValueError("Invalid required/properties structure")

    if not required or len(required) != len(set(required)):
        raise ValueError("Required fields must be nonempty and unique")

    if len(required) > 20 or len(properties) > 30:
        raise ValueError("Too many schema fields")

    for field in required:
        if not isinstance(field, str) or not IDENTIFIER.fullmatch(field):
            raise ValueError("Invalid required field name")
        if field not in properties:
            raise ValueError(f"Missing definition for '{field}'")

    for field, definition in properties.items():
        if not isinstance(field, str) or not IDENTIFIER.fullmatch(field):
            raise ValueError("Invalid property name")

        if not isinstance(definition, dict):
            raise ValueError(f"Invalid definition for '{field}'")

        if not set(definition).issubset({"type", "const", "minLength"}):
            raise ValueError(f"Unsupported schema keywords for '{field}'")

        field_type = definition.get("type")

        if field_type not in SUPPORTED_TYPES:
            raise ValueError(f"Unsupported type for '{field}'")

        if "minLength" in definition:
            minimum = definition["minLength"]
            if (
                field_type != "string"
                or type(minimum) is not int
                or minimum < 0
                or minimum > 1000
            ):
                raise ValueError(f"Invalid minLength for '{field}'")

        if "const" in definition:
            value = definition["const"]
            matches = {
                "string": lambda x: isinstance(x, str),
                "integer": lambda x: type(x) is int,
                "number": lambda x: type(x) in (int, float),
                "boolean": lambda x: type(x) is bool,
                "array": lambda x: isinstance(x, list),
                "object": lambda x: isinstance(x, dict),
            }

            if not matches[field_type](value):
                raise ValueError(f"Invalid const type for '{field}'")

            if (
                field_type == "string"
                and len(value) < definition.get("minLength", 0)
            ):
                raise ValueError(f"const violates minLength for '{field}'")


def register_capability_schemas(
    agent_id: str,
    schemas: dict[str, Any],
) -> dict[str, Any]:

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError("Agent is not registered")

    if manifest.status != "inactive":
        raise ValueError(
            "Schemas can only be registered while agent is inactive"
        )

    if not isinstance(schemas, dict) or not schemas:
        raise ValueError("At least one capability schema is required")

    if not set(schemas).issubset(set(manifest.capabilities)):
        raise ValueError("Schema contains undeclared capabilities")

    if not set(schemas) == set(manifest.capabilities):
        raise ValueError(
            "All declared capabilities must have schemas"
        )

    for capability, schema in schemas.items():
        validate_schema_definition(schema)

    content = json.dumps(
        schemas, indent=4, sort_keys=True, allow_nan=False
    ).encode("utf-8")

    if len(content) > MAX_SCHEMA_BYTES:
        raise ValueError("Capability schema document is too large")

    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

    # Use the validated ID from the existing manifest.
    path = SCHEMA_DIR / f"{manifest.agent_id}.json"

    # No silent overwrite of previously approved or submitted schemas.
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content.decode("utf-8"))
    except FileExistsError:
        raise ValueError(
            "Schemas already registered; explicit revision workflow required"
        )

    return {
        "agent_id": agent_id,
        "status": "registered",
        "capabilities_registered": sorted(schemas),
        "schema_path": str(path),
        "agent_status": manifest.status,
        "execution_performed": False,
    }


def get_dynamic_capability_schemas(agent_id: str) -> dict[str, Any]:

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError("Agent is not registered")

    path = SCHEMA_DIR / f"{manifest.agent_id}.json"

    if not path.is_file():
        return {}

    if path.stat().st_size > MAX_SCHEMA_BYTES:
        raise ValueError("Stored schema exceeds size limit")

    schemas = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(schemas, dict):
        raise ValueError("Invalid stored schema document")

    if set(schemas) != set(manifest.capabilities):
        raise ValueError("Stored schemas do not match agent manifest")

    for schema in schemas.values():
        validate_schema_definition(schema)

    return deepcopy(schemas)
