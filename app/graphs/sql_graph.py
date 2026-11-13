from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from app.agents.sql_agent import sql_agent

class SQLState(TypedDict, total=False):
    action: str
    table_name: str
    limit: int
    sql: str
    result: Any
    status: str

builder = StateGraph(SQLState)
builder.add_node("sql_agent", sql_agent)
builder.add_edge(START, "sql_agent")
builder.add_edge("sql_agent", END)

sql_graph = builder.compile()
