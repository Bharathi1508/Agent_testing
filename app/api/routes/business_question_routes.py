from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.dynamic_business_metadata import retrieve_metadata, normalize_rows
from app.services.metadata_service import list_tables, get_columns

router = APIRouter(prefix="/api/business-metadata", tags=["Business Metadata"])

class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)

class BulkRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)


def validate_candidate(candidate):
    # Schema check against current Unity Catalog metadata; NOT independent semantic assurance.
    table = candidate["table_name"]
    reference = normalize_rows(get_columns(table), ["column_name", "data_type", "comment"])
    indexed = {str(row["column_name"]).lower(): str(row.get("data_type", "")).upper() for row in reference}
    checks = []
    for col in candidate.get("columns", []):
        name = str(col["column_name"])
        expected_type = indexed.get(name.lower())
        valid = expected_type is not None and expected_type == str(col.get("data_type", "")).upper()
        checks.append({"column": name, "valid": valid})
    return {
        **candidate,
        "schema_status": "PASS" if checks and all(c["valid"] for c in checks) else "INCONCLUSIVE" if not checks else "FAIL",
        "semantic_status": "INCONCLUSIVE",
        "checks": checks,
    }


def evaluate(question):
    result = retrieve_metadata(question)
    validated = []
    for candidate in result.get("relevant_metadata", []):
        try:
            validated.append(validate_candidate(candidate))
        except Exception as exc:
            validated.append({**candidate, "schema_status": "ERROR", "semantic_status": "INCONCLUSIVE", "checks": [], "error": str(exc)})
    return {
        "question": question,
        "status": result["status"],
        "total_candidates": result["total_candidates"],
        "relevant_metadata": validated,
        "assurance_status": "INCONCLUSIVE",
        "assurance_note": "Schema checks use current catalog metadata. Semantic relevance and completeness are not independently verified; SQL execution is not authorized by this result.",
    }


@router.post("/ask")
def ask(request: QuestionRequest):
    try:
        return evaluate(request.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Metadata lookup failed: {exc}") from exc


def generate_questions(limit):
    tables = normalize_rows(list_tables(), ["table_name", "table_type"])
    questions = []
    seen = set()
    def add(q):
        if q not in seen and len(questions) < limit:
            questions.append(q)
            seen.add(q)
    for row in tables:
        table = str(row["table_name"])
        if not table.startswith("gold_"):
            continue
        add(f"Show the schema of {table}")
        columns = normalize_rows(get_columns(table), ["column_name", "data_type", "comment"])
        for col in columns:
            name = str(col["column_name"])
            if name.endswith("_id"):
                add(f"Show {name} from {table}")
            elif name.endswith("_date") or name in ("snapshot_date",):
                add(f"Show records by {name} in {table}")
            elif any(t in name for t in ("amount", "balance", "total_", "rate", "score", "count", "installment")):
                add(f"What is the total {name} in {table}?")
            elif name.endswith("_status") or name.endswith("_type"):
                add(f"Show records grouped by {name} in {table}")
            if len(questions) >= limit:
                break
        if len(questions) >= limit:
            break
    return questions


@router.post("/bulk")
def bulk(request: BulkRequest):
    try:
        questions = generate_questions(request.limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {exc}") from exc
    results = []
    for question in questions:
        try:
            results.append(evaluate(question))
        except Exception as exc:
            results.append({"question": question, "status": "ERROR", "assurance_status": "ERROR", "relevant_metadata": [], "error": str(exc)})
    return {"generated": len(questions), "results": results,
            "note": "These are schema-derived test prompts, not all possible business questions or verified expected answers."}
