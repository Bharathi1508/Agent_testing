
from app.graphs.metadata_graph import graph as metadata_graph
from app.graphs.sql_graph import sql_graph


def supervisor_agent(state):
    agent_type = state.get("agent_type")

    if agent_type == "metadata":
        result = metadata_graph.invoke({
            "action": state.get("action"),
            "table_name": state.get("table_name"),
            "column_name": state.get("column_name")
        })

    elif agent_type == "sql":
        result = sql_graph.invoke({
            "action": state.get("action"),
            "table_name": state.get("table_name"),
            "limit": state.get("limit", 5)
        })

    else:
        return {
            "status": "unsupported",
            "result": "Unknown agent type"
        }

    return {
        "status": "success",
        "selected_agent": agent_type,
        "result": result
    }
