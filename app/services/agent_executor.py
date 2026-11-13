
"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Module:
    Agent Executor

Purpose:
    Execute registered agents using their manifests,
    validate incoming payloads, and enforce trusted
    local execution restrictions.

Responsibilities:
    1. Execute registered agents using their manifests.
    2. Support the existing LangGraph Metadata Agent.
    3. Validate agent payloads and required fields.
    4. Enforce local agent capability allowlists.
    5. Verify manifest capability declarations.
    6. Return structured input-validation errors.
    7. Reject unsupported execution types.

Inputs:
    - AgentManifest
    - Execution payload dictionary

Outputs:
    - Agent execution result dictionary
    - AgentInputValidationError for invalid inputs
    - AgentExecutionError for execution failures

Security:
    - Only trusted local handlers may execute.
    - Unknown local agents are rejected.
    - Capabilities must be allowlisted and declared.
    - Databricks and REST adapters remain disabled.
    - Governance authorization belongs to the
      Dynamic Supervisor.

IMPORTANT:
    Do not import the Dynamic Supervisor here.
    Do not expose execute_agent as an unauthenticated
    API endpoint.
"""

from typing import Any

from app.registry.agent_models import AgentManifest


# =====================================================
# 1. CUSTOM EXCEPTIONS
# =====================================================

class AgentExecutionError(Exception):
    """
    Raised when an agent cannot be executed.

    Examples:
        - Missing trusted local handler
        - Unsupported execution type
        - Agent graph execution failure
        - Invalid agent execution response
    """


class AgentInputValidationError(AgentExecutionError):
    """
    Raised when an agent receives invalid input.

    This exception contains a structured error code
    that can be verified by the adversarial response
    adapter.

    Supported error codes:
        INVALID_INPUT
        INVALID_ACTION
    """

    def __init__(
        self,
        message: str,
        error_code: str = "INVALID_INPUT",
    ):
        super().__init__(message)
        self.error_code = error_code


# =====================================================
# 2. METADATA AGENT EXECUTION
# =====================================================

def execute_metadata_agent(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute the existing LangGraph Metadata Agent.

    The graph invokes the metadata_agent node,
    which calls the metadata tools and services.

    Input:
        Validated Metadata Agent payload.

    Output:
        Dictionary returned by the LangGraph graph.
    """

    from app.graphs.metadata_graph import graph

    result = graph.invoke(payload.copy())

    if not isinstance(result, dict):
        raise AgentExecutionError(
            "Metadata Agent returned an invalid response. "
            "Expected a dictionary."
        )

    return result


# =====================================================
# 3. TRUSTED LOCAL AGENT HANDLERS
# =====================================================

LOCAL_AGENT_HANDLERS = {
    "metadata_agent_001": execute_metadata_agent,
}


# =====================================================
# 4. LOCAL AGENT CAPABILITY ALLOWLIST
# =====================================================

LOCAL_AGENT_CAPABILITIES = {
    "metadata_agent_001": {
        "list_tables",
        "get_columns",
        "check_column",
        "search_columns",
    }
}


# =====================================================
# 5. METADATA ACTION REQUIRED FIELDS
# =====================================================

METADATA_ACTION_REQUIRED_FIELDS = {
    "list_tables": [],
    "get_columns": ["table_name"],
    "check_column": [
        "table_name",
        "column_name",
    ],
    "search_columns": ["column_name"],
}


# =====================================================
# 6. METADATA PAYLOAD VALIDATION
# =====================================================

def validate_metadata_payload(
    payload: dict[str, Any],
) -> str:
    """
    Validate Metadata Agent input payload.

    Validation rules:
        1. Payload must be a dictionary.
        2. Action must be a non-empty string.
        3. Action must be supported.
        4. Required fields must be non-empty strings.

    Returns:
        Normalized action name.

    Raises:
        AgentInputValidationError:
            INVALID_INPUT for malformed payloads.
            INVALID_ACTION for unsupported actions.
    """

    # -------------------------------------------------
    # Validate payload structure
    # -------------------------------------------------

    if not isinstance(payload, dict):
        raise AgentInputValidationError(
            "Metadata Agent payload must be a dictionary.",
            error_code="INVALID_INPUT",
        )

    # -------------------------------------------------
    # Validate action type
    # -------------------------------------------------

    action = payload.get("action")

    if not isinstance(action, str):
        raise AgentInputValidationError(
            "Metadata Agent payload must contain "
            "a valid string 'action'.",
            error_code="INVALID_INPUT",
        )

    # -------------------------------------------------
    # Normalize action
    # -------------------------------------------------

    action = action.strip().lower()

    if not action:
        raise AgentInputValidationError(
            "Metadata Agent action cannot be empty.",
            error_code="INVALID_INPUT",
        )

    # -------------------------------------------------
    # Validate supported action
    # -------------------------------------------------

    if action not in METADATA_ACTION_REQUIRED_FIELDS:
        raise AgentInputValidationError(
            f"Unsupported Metadata Agent action: '{action}'.",
            error_code="INVALID_ACTION",
        )

    # -------------------------------------------------
    # Validate required fields
    # -------------------------------------------------

    required_fields = METADATA_ACTION_REQUIRED_FIELDS[
        action
    ]

    for field in required_fields:

        value = payload.get(field)

        if not isinstance(value, str):
            raise AgentInputValidationError(
                f"Action '{action}' requires a "
                f"non-empty string field '{field}'.",
                error_code="INVALID_INPUT",
            )

        if not value.strip():
            raise AgentInputValidationError(
                f"Action '{action}' requires a "
                f"non-empty string field '{field}'.",
                error_code="INVALID_INPUT",
            )

    return action


# =====================================================
# 7. MAIN AGENT EXECUTOR
# =====================================================

def execute_agent(
    manifest: AgentManifest,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute an agent based on its registered manifest.

    Called by:
        dynamic_supervisor_service.py

    Input:
        manifest:
            Registered agent manifest.

        payload:
            Execution request.

    Output:
        Agent execution result dictionary.

    Security:
        This function must only be called through
        an authorized orchestration flow.
    """

    # -------------------------------------------------
    # Step 1: Validate manifest
    # -------------------------------------------------

    if manifest is None:
        raise AgentExecutionError(
            "Agent manifest is required."
        )

    # -------------------------------------------------
    # Step 2: Validate payload
    # -------------------------------------------------

    if not isinstance(payload, dict):
        raise AgentInputValidationError(
            "Agent payload must be a dictionary.",
            error_code="INVALID_INPUT",
        )

    # -------------------------------------------------
    # Step 3: Identify agent
    # -------------------------------------------------

    agent_id = manifest.agent_id
    execution_type = manifest.execution_type

    # -------------------------------------------------
    # Step 4: Handle local agents
    # -------------------------------------------------

    if execution_type == "local":

        handler = LOCAL_AGENT_HANDLERS.get(
            agent_id
        )

        if handler is None:
            raise AgentExecutionError(
                f"No trusted local handler registered "
                f"for agent '{agent_id}'."
            )

        # ---------------------------------------------
        # Step 5: Validate agent-specific payload
        # ---------------------------------------------

        if agent_id == "metadata_agent_001":

            action = validate_metadata_payload(
                payload
            )

        else:
            raise AgentExecutionError(
                f"No payload validator configured "
                f"for local agent '{agent_id}'."
            )

        # ---------------------------------------------
        # Step 6: Verify local capability allowlist
        # ---------------------------------------------

        allowed_capabilities = (
            LOCAL_AGENT_CAPABILITIES.get(
                agent_id,
                set(),
            )
        )

        if action not in allowed_capabilities:
            raise AgentExecutionError(
                f"Action '{action}' is not allowlisted "
                f"for agent '{agent_id}'."
            )

        # ---------------------------------------------
        # Step 7: Verify manifest capabilities
        # ---------------------------------------------

        manifest_capabilities = {
            str(capability).strip().lower()
            for capability in manifest.capabilities
        }

        if action not in manifest_capabilities:
            raise AgentExecutionError(
                f"Action '{action}' is not declared "
                f"in the manifest for '{agent_id}'."
            )

        # ---------------------------------------------
        # Step 8: Prepare safe execution payload
        # ---------------------------------------------

        safe_payload = payload.copy()

        safe_payload["action"] = action

        # ---------------------------------------------
        # Step 9: Execute trusted local agent
        # ---------------------------------------------

        try:

            result = handler(
                safe_payload
            )

        except AgentInputValidationError:
            # Preserve structured validation errors.
            raise

        except Exception as exc:

            raise AgentExecutionError(
                f"Local agent '{agent_id}' "
                f"execution failed: {exc}"
            ) from exc

        # ---------------------------------------------
        # Step 10: Validate execution result
        # ---------------------------------------------

        if not isinstance(result, dict):
            raise AgentExecutionError(
                "Local agent returned an invalid result."
            )

        return result

    # -------------------------------------------------
    # Step 11: Databricks execution
    # -------------------------------------------------

    elif execution_type == "databricks":

        raise AgentExecutionError(
            "Databricks Agent execution adapter "
            "has not been configured yet."
        )

    # -------------------------------------------------
    # Step 12: REST execution
    # -------------------------------------------------

    elif execution_type == "rest":

        raise AgentExecutionError(
            "REST Agent execution adapter "
            "has not been configured yet."
        )

    # -------------------------------------------------
    # Step 13: Unsupported execution type
    # -------------------------------------------------

    else:

        raise AgentExecutionError(
            f"Unsupported execution type: "
            f"'{execution_type}'."
        )
