from app.services.metadata_evaluation_integration import run_independent_evaluation
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.supervisor_metadata_selector import select_metadata

router = APIRouter(
    prefix="/api/supervisor-metadata",
    tags=["Supervisor Metadata Selection"]
)

class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

@router.post("/select")
def select_question_metadata(request: QuestionRequest):
    return select_metadata(request.question)


@router.post("/validate")
def validate_question_metadata(request: QuestionRequest):
    from app.services.live_metadata_validator import (
        validate_with_live_schema,
    )

    selection = select_metadata(request.question)

    validation = validate_with_live_schema(
        request.question,
        selection,
    )

    independent_evaluation = run_independent_evaluation(
        selection,
        validation,
    )

    return {
        "selection": selection,
        "validation": validation,
        "independent_evaluation": independent_evaluation,
    }


from pydantic import BaseModel, Field
from fastapi import HTTPException


class BulkMetadataRequest(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=1000)
    max_workers: int = Field(default=2, ge=1, le=4)


@router.post("/bulk-validate")
def bulk_validate_metadata(request: BulkMetadataRequest):
    from app.services.bulk_metadata_supervisor import (
        run_bulk_metadata_assurance,
    )

    try:
        return run_bulk_metadata_assurance(
            questions=request.questions,
            max_workers=request.max_workers,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.post("/negative-tests")
def run_metadata_negative_tests():
    from app.services.metadata_negative_testing import (
        run_negative_metadata_tests,
    )
    return run_negative_metadata_tests()

