
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.tools.llm_metadata_tools import metadata_tools

load_dotenv()

model = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    temperature=0,
)

SYSTEM_PROMPT = """
You are a Databricks Unity Catalog Metadata Agent.

Your responsibilities:
1. Answer questions about Gold tables and columns.
2. Use metadata tools to verify information.
3. Never invent table names, columns, or data types.
4. Only describe metadata visible through the tools.
5. If information is unavailable, explain the limitation.
6. Never execute data-modifying SQL.
"""

intelligent_graph = create_react_agent(
    model=model,
    tools=metadata_tools,
    prompt=SYSTEM_PROMPT,
)
