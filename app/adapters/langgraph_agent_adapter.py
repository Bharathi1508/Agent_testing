"""
HEAAP Phase 17.3
LangGraph Agent Adapter.

Restricted to explicitly approved local graph implementations.
"""

from copy import deepcopy

from app.adapters.real_agent_contract import (
    AgentExecutionRequest,
    AgentExecutionResult,
    RealAgentAdapter,
)

from app.adapters.approved_graph_registry import (
    get_approved_graph,
)

from app.registry.agent_registry import get_registered_agent


class LangGraphAgentAdapter(RealAgentAdapter):

    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResult:

        manifest = get_registered_agent(request.agent_id)

        if manifest is None:
            raise ValueError("Agent is not registered")

        if manifest.execution_type != "local":
            raise ValueError(
                "LangGraph adapter supports local agents only"
            )

        if manifest.framework.lower() != "langgraph":
            raise ValueError(
                "Agent framework is not LangGraph"
            )

        if request.capability not in manifest.capabilities:
            raise ValueError(
                "Capability is not registered"
            )

        graph = get_approved_graph(request.agent_id)

        if graph is None:
            raise PermissionError(
                "No approved LangGraph implementation found"
            )

        if not isinstance(request.payload, dict):
            raise ValueError("Payload must be a dictionary")

        # Development-only: sql_agent_001 remains inactive.
        # This invocation is an explicitly approved local test,
        # not production activation.
        if request.agent_id != "sql_agent_001":
            raise PermissionError(
                "Only sql_agent_001 is allowed in Phase 17.3"
            )

        if manifest.status != "inactive":
            raise PermissionError(
                "Phase 17.3 requires inactive onboarding status"
            )

        state = graph.invoke({
            "payload": deepcopy(request.payload)
        })

        response = state.get("response")

        if not isinstance(response, dict):
            raise RuntimeError(
                "LangGraph response must be a dictionary"
            )

        return AgentExecutionResult(
            agent_id=request.agent_id,
            capability=request.capability,
            test_id=request.test_id,
            status=response.get("status", "unknown"),
            response=response,
            error_code=response.get("error_code"),
            execution_target="langgraph_local",
        )
