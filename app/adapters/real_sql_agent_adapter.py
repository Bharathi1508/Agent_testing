from typing import Any

from app.adapters.real_agent_contract import (
    AgentExecutionRequest,
    AgentExecutionResult,
    RealAgentAdapter,
)
from app.registry.agent_registry import get_registered_agent
from app.registry.dynamic_capability_registry import (
    get_dynamic_capability_schemas,
)
from app.agents.real_sql_agent import run_sql_agent
from app.services.real_sql_validation_service import (
    validate_generated_sql,
)


AGENT_ID = "sql_agent_real_001"
EXECUTION_TARGET = "langgraph_local"


class RealSQLAgentAdapter(RealAgentAdapter):

    def _result(
        self,
        request: AgentExecutionRequest,
        status: str,
        response: dict,
        error_code: str | None = None,
    ) -> AgentExecutionResult:

        return AgentExecutionResult(
            agent_id=request.agent_id,
            capability=request.capability,
            test_id=request.test_id,
            status=status,
            response=response,
            error_code=error_code,
            execution_target=EXECUTION_TARGET,
        )

    def _reject(
        self,
        request: AgentExecutionRequest,
        message: str,
        error_code: str = "INVALID_INPUT",
    ) -> AgentExecutionResult:

        return self._result(
            request=request,
            status="error",
            response={
                "message": message,
                "database_executed": False,
            },
            error_code=error_code,
        )

    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResult:

        if request.agent_id != AGENT_ID:
            return self._reject(
                request,
                "Adapter does not support this agent",
                "UNSUPPORTED_AGENT",
            )

        agent = get_registered_agent(AGENT_ID)

        if agent is None:
            return self._reject(
                request,
                "Agent is not registered",
                "AGENT_NOT_REGISTERED",
            )

        # Explicitly approved local test adapter.
        # This does not activate the agent for normal routing.
        if agent.status not in {"inactive", "active"}:
            return self._reject(
                request,
                "Agent status does not permit local testing",
                "AGENT_NOT_AVAILABLE",
            )

        schemas = get_dynamic_capability_schemas(AGENT_ID)

        if (
            request.capability not in agent.capabilities
            or request.capability not in schemas
        ):
            return self._reject(
                request,
                "Capability is not registered",
                "UNSUPPORTED_CAPABILITY",
            )

        payload = request.payload

        if not isinstance(payload, dict):
            return self._reject(
                request,
                "Payload must be a JSON object",
            )

        if request.capability == "generate_sql":

            if set(payload) != {"action", "question"}:
                return self._reject(
                    request,
                    "generate_sql requires only action and question",
                )

            if payload.get("action") != "generate_sql":
                return self._reject(
                    request,
                    "Invalid action for generate_sql",
                )

            question = payload.get("question")

            if (
                not isinstance(question, str)
                or not question.strip()
                or len(question) > 500
            ):
                return self._reject(
                    request,
                    "question must be a nonempty string of at most 500 characters",
                )

            try:
                output = run_sql_agent(question)
            except Exception:
                return self._reject(
                    request,
                    "Local SQL generation failed",
                    "AGENT_EXECUTION_ERROR",
                )

            if not isinstance(output, dict):
                return self._reject(
                    request,
                    "Agent returned an invalid response",
                    "INVALID_AGENT_RESPONSE",
                )

            return self._result(
                request,
                status=output.get("status", "error"),
                response=output,
                error_code=output.get("error_code"),
            )

        if request.capability == "validate_sql":

            if set(payload) != {"action", "sql_query"}:
                return self._reject(
                    request,
                    "validate_sql requires only action and sql_query",
                )

            if payload.get("action") != "validate_sql":
                return self._reject(
                    request,
                    "Invalid action for validate_sql",
                )

            output = validate_generated_sql(
                payload.get("sql_query")
            )

            return self._result(
                request,
                status=output["status"],
                response=output,
                error_code=output.get("error_code"),
            )

        return self._reject(
            request,
            "Unsupported capability",
            "UNSUPPORTED_CAPABILITY",
        )
