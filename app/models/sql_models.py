from pydantic import BaseModel, Field


class SQLRequest(BaseModel):
    action: str
    table_name: str
    limit: int = Field(default=5, ge=1, le=100)