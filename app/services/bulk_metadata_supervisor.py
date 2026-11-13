from collections import Counter
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from app.services.supervisor_metadata_selector import select_metadata
from app.services.live_metadata_validator import validate_with_live_schema


def _evaluate_one(index, question):
    try:
        selection = select_metadata(question)
        validation = validate_with_live_schema(question, selection)

        status = str(
            validation.get("validation_status", "REVIEW")
        ).upper()

        if status not in ("PASS", "FAIL", "REVIEW"):
            status = "REVIEW"

        return {
            "index": index,
            "question": question,
            "status": status,
            "primary_table": selection.get("primary_table"),
            "selection": selection,
            "validation": validation,
        }

    except Exception as exc:
        return {
            "index": index,
            "question": question,
            "status": "ERROR",
            "primary_table": None,
            "selection": None,
            "validation": None,
            "error": str(exc),
        }


def run_bulk_metadata_assurance(questions, max_workers=2):
    if not questions:
        raise ValueError("At least one question is required.")

    if len(questions) > 1000:
        raise ValueError("Maximum 1000 questions per request.")

    if any(not isinstance(q, str) or not q.strip() for q in questions):
        raise ValueError("Every question must be a non-empty string.")

    workers = max(1, min(int(max_workers), 4))

    results = [None] * len(questions)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_evaluate_one, i, q): i
            for i, q in enumerate(questions, start=1)
        }

        for future in as_completed(futures):
            result = future.result()
            results[result["index"] - 1] = result

    counts = Counter(result["status"] for result in results)

    return {
        "run_id": str(uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(questions),
        "summary": {
            "pass": counts["PASS"],
            "fail": counts["FAIL"],
            "review": counts["REVIEW"],
            "error": counts["ERROR"],
        },
        "results": results,
    }
