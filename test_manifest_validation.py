
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from app.discovery.manifest_validator import (
    validate_discovered_agent,
)


candidate = {
    "agent_id": "metadata_agent_001",
    "agent_name": "Metadata Agent",
    "provider": "langgraph",
    "execution_type": "local",
    "capabilities": [
        "list_tables",
        "describe_table"
    ],
    "description": "Retrieves Databricks metadata",
    "version": "1.0.0"
}

result = validate_discovered_agent(candidate)

print(result.model_dump_json(indent=2))
