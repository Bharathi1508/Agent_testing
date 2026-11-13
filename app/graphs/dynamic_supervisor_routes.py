
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graphs.dynamic_supervisor_graph import (
    dynamic_supervisor_graph

)
app.include_router(dynamic_supervisor_router)

router = APIRouter(
    prefix="/supervisor",
    tags=["Dynamic Supervisor"]
)


class DynamicSupervisorRequest(BaseModel):
    capability: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=100)


@router.post("/dynamic-run")
def dynamic_run(request: DynamicSupervisorRequest):
    try:
        return dynamic_supervisor_graph.invoke(
            request.model_dump(exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )
