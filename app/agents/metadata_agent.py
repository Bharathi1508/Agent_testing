from app.tools.metadata_tools import search_columns_tool
from app.tools.metadata_tools import (
    list_tables_tool,
    get_columns_tool,
    check_column_tool,
)


def metadata_agent(state):
    action = state.get("action")

    if action == "list_tables":
        result = list_tables_tool()

    elif action == "get_columns":
        result = get_columns_tool(state["table_name"])

    elif action == "check_column":
        result = check_column_tool(
            state["table_name"],
            state["column_name"]
        )
    elif action == "search_columns":
        result = search_columns_tool(
        state["column_name"]
    )
    else:
        return {
            "status": "unsupported",
            "result": "Unknown metadata action"
        }

    return {
        "status": "success",
        "result": result
    }