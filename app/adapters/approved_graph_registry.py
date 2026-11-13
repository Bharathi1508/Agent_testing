"""
HEAAP Phase 17.3
Trusted LangGraph graph registry.

Only administrator-controlled code may add entries.
"""

from app.agents.langgraph_sql_agent import sql_graph


APPROVED_GRAPHS = {
    "sql_agent_001": sql_graph,
}


def get_approved_graph(agent_id: str):
    return APPROVED_GRAPHS.get(agent_id)
