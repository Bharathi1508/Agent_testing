
from fastapi import APIRouter, HTTPException
from app.models.sql_models import SQLRequest
from app.graphs.sql_graph import sql_graph

router = APIRouter(prefix="/sql", tags=["SQL Agent"])


@router.post("/run")
def run_sql(request: SQLRequest):
    try:
        return sql_graph.invoke(request.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )
