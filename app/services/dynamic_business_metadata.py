import re

from app.agents.metadata_agent import metadata_agent
from app.services.metadata_service import list_tables, get_columns


STOPWORDS = {
    "what", "which", "who", "show", "list", "give",
    "find", "display", "the", "a", "an", "of",
    "for", "by", "in", "on", "with", "and",
    "are", "is", "have", "has", "from", "all",
    "me", "please", "how", "many"
}

SYNONYMS = {
    "customers": "customer",
    "loans": "loan",
    "installments": "installment",
    "accounts": "account",
    "transactions": "transaction",
    "balances": "balance",
    "payments": "payment",
    "branches": "branch",
    "complaints": "complaint",
    "overdue": "overdue",
}


def tokenize(text):
    words = re.findall(r"[a-zA-Z0-9]+", str(text).lower())

    result = set()

    for word in words:
        if word in STOPWORDS:
            continue

        word = SYNONYMS.get(word, word)

        if word.endswith("s") and len(word) > 4:
            word = word[:-1]

        result.add(word)

    return result


def normalize_rows(rows, names):
    if isinstance(rows, dict):
        rows = rows.get("rows", rows.get("result", []))

    result = []

    for row in rows or []:
        if isinstance(row, dict):
            result.append(row)
        elif hasattr(row, "asDict"):
            result.append(row.asDict())
        elif hasattr(row, "_asdict"):
            result.append(row._asdict())
        else:
            result.append(dict(zip(names, row)))

    return result


def retrieve_metadata(question):
    if not question or not question.strip():
        raise ValueError("Business question cannot be empty")

    question_terms = tokenize(question)

    tables = normalize_rows(
        list_tables(),
        ["table_name", "table_type"]
    )

    candidates = []

    for table in tables:
        table_name = str(table["table_name"])

        if not table_name.startswith("gold_"):
            continue

        response = metadata_agent({
            "action": "get_columns",
            "table_name": table_name
        })

        if response.get("status") != "success":
            continue

        columns = normalize_rows(
            response["result"],
            ["column_name", "data_type", "comment"]
        )

        table_terms = tokenize(table_name)

        selected_columns = []
        score = len(question_terms & table_terms) * 2

        for column in columns:
            column_name = str(column["column_name"])
            comment = str(column.get("comment") or "")

            column_terms = tokenize(column_name + " " + comment)

            overlap = question_terms & column_terms

            if overlap:
                selected_columns.append({
                    "column_name": column_name,
                    "data_type": column.get("data_type"),
                    "matched_terms": sorted(overlap)
                })

                score += len(overlap) * 3

        if score > 0:
            candidates.append({
                "table_name": table_name,
                "score": score,
                "columns": selected_columns
            })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return {
        "question": question,
        "status": "MATCHED" if candidates else "NO_MATCH",
        "total_candidates": len(candidates),
        "relevant_metadata": candidates[:5]
    }
