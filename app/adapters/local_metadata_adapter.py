from app.adapters.real_agent_contract import (
    RealAgentAdapter,
    AgentExecutionRequest,
    AgentExecutionResult,
)

from app.registry.agent_registry import get_registered_agent
from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
)
from app.services.adversarial_response_adapter import (
    adapt_adversarial_exception,
    adapt_adversarial_success,
)


class LocalMetadataAdapter(RealAgentAdapter):

    AGENT_ID = "metadata_agent_001"

    def execute(self, request):

        if request.agent_id != self.AGENT_ID:
            raise ValueError("Unsupported agent ID")

        manifest = get_registered_agent(request.agent_id)

        if manifest is None:
            raise ValueError("Agent not registered")

        if manifest.status != "active":
            raise ValueError("Agent is not active")

        if manifest.execution_type != "local":
            raise ValueError("Agent is not local")

        if request.capability not in manifest.capabilities:
            raise ValueError("Capability not registered")

        try:
            response = execute_supervisor_request(
                capability=request.capability,
                payload=request.payload.copy(),
                preferred_agent_id=request.agent_id,
            )

            normalized = adapt_adversarial_success(response)

        except Exception as exc:

            normalized = adapt_adversarial_exception(exc)

        if not isinstance(normalized, dict):
            raise RuntimeError(
                "Response adapter returned an invalid format"
            )

        return AgentExecutionResult(
            agent_id=request.agent_id,
            capability=request.capability,
            test_id=request.test_id,
            status=normalized.get("status", "unknown"),
            response=normalized,
            error_code=normalized.get("error_code"),
            execution_target="real_local_metadata",
        )
