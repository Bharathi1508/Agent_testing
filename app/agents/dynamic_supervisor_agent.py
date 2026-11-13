
from app.services.dynamic_router import resolve_agent
from app.services.agent_executor import execute_agent


def dynamic_supervisor_agent(state):
    capability = state["capability"]
    selected = resolve_agent(capability)

    payload = {
        "action": capability
    }

    for field in (
        "table_name",
        "column_name",
        "limit",
        "question"
    ):
        if state.get(field) is not None:
            payload[field] = state[field]

    result = execute_agent(
        selected,
        payload
    )

    return {
        "status": "success",
        "selected_agent": selected.agent_id,
        "execution_type": selected.execution_type,
        "capability": capability,
        "result": result
    }
