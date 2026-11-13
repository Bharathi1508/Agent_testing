
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END

from app.agents.supervisor_agent import supervisor_agent


class SupervisorState(TypedDict, total=False):
    agent_type: str
    action: str
    table_name: str
    column_name: str
    limit: int
    status: str
    selected_agent: str
    result: Any


builder = StateGraph(SupervisorState)

builder.add_node("supervisor", supervisor_agent)

builder.add_edge(START, "supervisor")
builder.add_edge("supervisor", END)

supervisor_graph = builder.compile()
