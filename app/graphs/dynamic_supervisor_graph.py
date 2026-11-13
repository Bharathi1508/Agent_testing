
from typing import TypedDict, Any

from langgraph.graph import StateGraph, START, END
from app.agents.dynamic_supervisor_agent import (
    dynamic_supervisor_agent
)


class DynamicSupervisorState(TypedDict, total=False):
    capability: str
    table_name: str
    column_name: str
    limit: int
    status: str
    selected_agent: str
    result: Any


builder = StateGraph(DynamicSupervisorState)

builder.add_node(
    "dynamic_supervisor",
    dynamic_supervisor_agent
)

builder.add_edge(START, "dynamic_supervisor")
builder.add_edge("dynamic_supervisor", END)

dynamic_supervisor_graph = builder.compile()
