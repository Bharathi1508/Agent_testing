
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class AgentManifest(BaseModel):
    agent_id: str = Field(
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$"
    )
    name: str
    version: str
    framework: str
    environment: str
    capabilities: list[str] = Field(min_length=1)

    execution_type: Literal[
        "local",
        "databricks"
    ] = "local"

    # Databricks serving endpoint name,
    # not a complete arbitrary URL.
    endpoint_name: str | None = None

    status: Literal[
        "active",
        "inactive"
    ] = "inactive"

    @model_validator(mode="after")
    def validate_endpoint(self):
        if self.execution_type == "databricks":
            if not self.endpoint_name:
                raise ValueError(
                    "Databricks agents require endpoint_name"
                )
        return self
