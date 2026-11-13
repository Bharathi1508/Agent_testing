from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END

from app.agents.metadata_agent import metadata_agent


class MetadataState(TypedDict, total=False):
    action: str
    table_name: str
    column_name: str
    result: Any
    status: str


builder = StateGraph(MetadataState)

builder.add_node("metadata_agent", metadata_agent)

builder.add_edge(START, "metadata_agent")
builder.add_edge("metadata_agent", END)

graph = builder.compile()