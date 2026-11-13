
import re


def parse_question(question: str):
    text = question.strip()
    lower = text.lower()

    if re.search(r"\b(list|show|what)\b", lower) and (
        "tables" in lower
    ):
        return {"action": "list_tables"}

    match = re.search(
        r"(?:columns|schema)\s+(?:in|of|for)\s+"
        r"([a-zA-Z_][a-zA-Z0-9_]*)",
        text,
        re.IGNORECASE
    )

    if match:
        return {
            "action": "get_columns",
            "table_name": match.group(1)
        }

    return {
        "action": "unsupported",
        "message": "Could not identify metadata request"
    }
