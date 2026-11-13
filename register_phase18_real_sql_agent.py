"""
HEAAP Phase 18.2
Controlled registration of the real LangGraph SQL Agent.

This script:
- Verifies the agent implementation
- Declares the agent's capabilities
- Registers its manifest and schemas
- Leaves the agent inactive
- Never invokes external endpoints
"""

import json
from pathlib import Path

from app.agents.real_sql_agent import (
    run_sql_agent,
    SQL_TEMPLATES,
)

from app.registry.agent_models import AgentManifest
from app.registry.agent_registry import (
    register_agent,
    get_registered_agent,
)

from app.registry.dynamic_capability_registry import (
    register_capability_schemas,
    get_dynamic_capability_schemas,
)


AGENT_ID = "sql_agent_real_001"


CAPABILITY_SCHEMAS = {
    "generate_sql": {
        "required": ["action", "question"],
        "properties": {
            "action": {
                "type": "string",
                "const": "generate_sql",
            },
            "question": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
            },
        },
    },
    "validate_sql": {
        "required": ["action", "sql_query"],
        "properties": {
            "action": {
                "type": "string",
                "const": "validate_sql",
            },
            "sql_query": {
                "type": "string",
                "minLength": 1,
            },
        },
    },
}

def main():

    # Step 1: Verify that the agent implementation works.
    sample = run_sql_agent("total annual premium")

    if sample["status"] != "success":
        raise RuntimeError(
            "Real SQL Agent verification failed"
        )

    if sample["database_executed"] is not False:
        raise RuntimeError(
            "Unexpected database execution"
        )

    print("PASSED: Real SQL Agent implementation verified")

    # Step 2: Build the manifest.
    manifest = AgentManifest(
        agent_id=AGENT_ID,
        name="HEAAP Real SQL Agent",
        version="1.0.0",
        framework="LangGraph",
        environment="local",
        capabilities=[
            "generate_sql",
            "validate_sql",
        ],
        execution_type="local",
        endpoint_name=None,
        status="inactive",
    )

    # Step 3: Check for an existing registration.
    existing = get_registered_agent(AGENT_ID)

    if existing is not None:
        print(
            "Agent already registered. "
            "Existing manifest preserved."
        )
    else:
        register_agent(manifest)
        print("PASSED: Agent manifest registered")

    # Step 4: Register capability schemas only if missing.
    existing_schemas = get_dynamic_capability_schemas(
        AGENT_ID
    )

    if existing_schemas:
        print(
            "Capability schemas already exist. "
            "Existing schemas preserved."
        )
    else:
        register_capability_schemas(
            AGENT_ID,
            CAPABILITY_SCHEMAS,
        )
        print("PASSED: Capability schemas registered")

    # Step 5: Read back the registry information.
    registered = get_registered_agent(AGENT_ID)

    schemas = get_dynamic_capability_schemas(
        AGENT_ID
    )

    if registered is None:
        raise RuntimeError("Agent registration missing")

    if set(registered.capabilities) != set(
        CAPABILITY_SCHEMAS
    ):
        raise RuntimeError(
            "Registered capabilities do not match"
        )

    if not schemas:
        raise RuntimeError(
            "Capability schemas could not be discovered"
        )

    if registered.status != "inactive":
        raise RuntimeError(
            "New agent must remain inactive"
        )

    print()
    print("=" * 55)
    print("PHASE 18.2 REGISTRATION SUMMARY")
    print("=" * 55)

    print("Agent ID:", registered.agent_id)
    print("Framework:", registered.framework)
    print("Environment:", registered.environment)
    print("Execution type:", registered.execution_type)
    print("Status:", registered.status)
    print("Capabilities:", registered.capabilities)
    print("Supported SQL templates:", len(SQL_TEMPLATES))
    print("Capability schemas:", list(schemas.keys()))
    print("Database execution: Disabled")
    print("Production approved: False")

    print()
    print("PHASE 18.2: REGISTRATION COMPLETED")


if __name__ == "__main__":
    main()
