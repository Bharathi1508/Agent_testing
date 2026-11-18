from app.services.dynamic_business_metadata import (
    retrieve_metadata,
    tokenize,
)
from app.services.metadata_validation_engine import match_reference


def select_metadata(question: str, retrieval: dict | None = None):
    retrieval = retrieval or retrieve_metadata(question)
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

    rule = match_reference(question)
    if rule is not None:
        primary = next(
            (
                candidate
                for candidate in evaluated
                if candidate["table_name"].lower() == rule["table"].lower()
            ),
            None,
        )
        return {
            "question": question,
            "primary_table": rule["table"],
            "selected_columns": list(rule["required_columns"]),
            "supporting_tables": [],
            "rejected_candidates": [
                {
                    "table_name": candidate["table_name"],
                    "reason": "Not selected by the approved reference rule",
                }
                for candidate in evaluated
                if candidate["table_name"].lower() != rule["table"].lower()
            ],
            "selection_status": "REFERENCE_MATCHED",
            "schema_status": (
                primary["schema_status"] if primary else "NOT_VERIFIED"
            ),
            "coverage": primary["coverage"] if primary else 0,
            "selection_source": "curated_reference",
            "reference_rule_id": rule["rule_id"],
            "expected_filter": rule["filter"],
            "relationships": list(rule.get("relationships", [])),
            "join_required": rule.get("join_required", False),
            "sql_execution_allowed": False,
            "note": (
                "Required metadata came from a curated code reference rule. "
                "The expected filter is a requirement, not proof that SQL "
                "applied it."
            ),
        }

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
            "selection_source": "heuristic",
            "reference_rule_id": None,
            "expected_filter": None,
            "relationships": [],
            "join_required": False,
            "note": (
                "No metadata candidate matched the question. "
                "SQL execution is blocked."
            ),
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
        "selection_source": "heuristic",
        "reference_rule_id": None,
        "expected_filter": None,
        "relationships": [],
        "join_required": False,
        "sql_execution_allowed": False,
        "note": (
            "This is a heuristic metadata proposal, not an "
            "independently verified semantic selection. "
            "Other candidates have not been proven irrelevant."
        ),
    }
