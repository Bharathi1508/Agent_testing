from app.services.dynamic_business_metadata import (
    retrieve_metadata,
    tokenize,
)

def select_metadata(question: str):
    retrieval = retrieve_metadata(question)
    question_terms = tokenize(question)

    candidates = retrieval.get("relevant_metadata", [])
    evaluated = []

    for candidate in candidates:
        table = candidate["table_name"]
        columns = candidate.get("columns", [])

        # Collect the business terms supported by the table's columns.
        covered_terms = set()
        for column in columns:
            covered_terms.update(column.get("matched_terms", []))

        coverage = (
            len(covered_terms & question_terms) / len(question_terms)
            if question_terms else 0
        )

        evaluated.append({
            "table_name": table,
            "score": candidate["score"],
            "coverage": round(coverage, 3),
            "columns": columns,
            "schema_status": "NOT_VERIFIED",
        })

    # Prefer question-term coverage, then existing ranking score.
    evaluated.sort(
        key=lambda x: (x["coverage"], x["score"]),
        reverse=True
    )

    if not evaluated:
        return {
            "question": question,
            "selection_status": "NO_MATCH",
            "primary_table": None,
            "selected_columns": [],
            "supporting_tables": [],
            "rejected_candidates": [],
            "sql_execution_allowed": False,
        }

    primary = evaluated[0]

    # Select fields matching the greatest number of question terms.
    ranked_columns = sorted(
        primary["columns"],
        key=lambda c: len(c.get("matched_terms", [])),
        reverse=True
    )

    selected_columns = [
        c["column_name"]
        for c in ranked_columns
        if c.get("matched_terms")
    ]

    # Retain identifiers available among the matched columns.
    # These may be needed for grouping or identifying records.
    for identifier in ("customer_id", "loan_id"):
        if (
            identifier in [c["column_name"] for c in primary["columns"]]
            and identifier not in selected_columns
        ):
            selected_columns.append(identifier)

    return {
        "question": question,
        "primary_table": primary["table_name"],
        "selected_columns": selected_columns,
        "supporting_tables": [],
        "rejected_candidates": [
            {
                "table_name": c["table_name"],
                "reason": "Not selected as primary candidate"
            }
            for c in evaluated[1:]
        ],
        "selection_status": "PENDING_SEMANTIC_VALIDATION",
        "schema_status": primary["schema_status"],
        "coverage": primary["coverage"],
        "sql_execution_allowed": False,
        "note": (
            "This is a heuristic metadata proposal, not an "
            "independently verified semantic selection. "
            "Other candidates have not been proven irrelevant."
        ),
    }
