from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.heaap_pipeline import run_pipeline


router = APIRouter(
    prefix="/api/heaap/pipeline",
    tags=["HEAAP Pipeline"],
)


class PipelineRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class BulkPipelineRequest(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=100)


@router.post("/validate")
def validate_pipeline(request: PipelineRequest):
    return run_pipeline(request.question)


@router.post("/validate/bulk")
def validate_pipeline_bulk(request: BulkPipelineRequest):
    if any(not question.strip() or len(question) > 2000 for question in request.questions):
        raise HTTPException(
            status_code=422,
            detail="Each question must contain 1 to 2000 characters.",
        )

    def run_question(question: str):
        try:
            return run_pipeline(question)
        except Exception as exc:
            return {
                "question": question,
                "metadata_assurance_status": "ERROR",
                "sql_generation_status": "NOT_STARTED",
                "sql_execution_status": "NOT_EXECUTED",
                "sql_execution_allowed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    with ThreadPoolExecutor(
        max_workers=min(4, len(request.questions))
    ) as executor:
        results = list(executor.map(run_question, request.questions))

    statuses = [
        result.get("metadata_assurance_status", "ERROR")
        for result in results
    ]
    return {
        "total": len(results),
        "summary": {
            "PASS": statuses.count("PASS"),
            "REVIEW": statuses.count("REVIEW"),
            "FAIL": statuses.count("FAIL"),
            "ERROR": statuses.count("ERROR"),
            "EXECUTED": sum(
                result.get("sql_execution_status") == "SUCCEEDED"
                for result in results
            ),
        },
        "results": results,
    }
