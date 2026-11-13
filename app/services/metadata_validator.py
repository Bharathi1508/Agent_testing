from typing import Any


def normalize_type(value: Any) -> str:
    value = str(value or "").upper().strip()
    aliases = {
        "BIGINT": "LONG",
        "INTEGER": "INT",
        "VARCHAR": "STRING",
    }
    return aliases.get(value, value)


def validate_metadata(agent_columns, trusted_columns):
    """
    Compare actual agent metadata with independently
    retrieved trusted metadata.
    """

    def index_columns(columns):
        result = {}

        for column in columns:
            name = str(column["column_name"]).lower().strip()

            if name in result:
                raise ValueError(
                    f"Duplicate column name: {name}"
                )

            result[name] = normalize_type(
                column["data_type"]
            )

        return result

    agent = index_columns(agent_columns)
    trusted = index_columns(trusted_columns)

    missing = sorted(set(trusted) - set(agent))
    unexpected = sorted(set(agent) - set(trusted))

    mismatches = []

    for name in sorted(set(agent) & set(trusted)):
        if agent[name] != trusted[name]:
            mismatches.append({
                "column": name,
                "agent_type": agent[name],
                "trusted_type": trusted[name],
            })

    matched = len(set(agent) & set(trusted)) - len(mismatches)

    total = len(trusted)

    accuracy = (
        round(matched / total * 100, 2)
        if total
        else 0.0
    )

    passed = (
        not missing
        and not unexpected
        and not mismatches
        and len(agent) == len(trusted)
    )

    return {
        "status": "PASS" if passed else "FAIL",
        "accuracy_score": accuracy,
        "agent_column_count": len(agent),
        "trusted_column_count": len(trusted),
        "missing_columns": missing,
        "unexpected_columns": unexpected,
        "type_mismatches": mismatches,
        "matched_columns": matched,
    }
