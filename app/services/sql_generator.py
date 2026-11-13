
import os

from app.services.metadata_service import get_columns

CATALOG = os.environ["DATABRICKS_CATALOG"]
SCHEMA = os.environ["DATABRICKS_SCHEMA"]


def quote_identifier(value: str) -> str:
    if not value or not value.replace("_", "").isalnum():
        raise ValueError("Invalid SQL identifier")
    return f"`{value}`"


def generate_top_loans_sql(
    table_name: str,
    limit: int = 5
):
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100")

    columns = get_columns(table_name)
    available = {c["column_name"] for c in columns}

    required = {
        "loan_id",
        "principal_amount_inr"
    }

    if not required.issubset(available):
        raise ValueError(
            "Required loan columns not found in table"
        )

    table = ".".join([
        quote_identifier(CATALOG),
        quote_identifier(SCHEMA),
        quote_identifier(table_name)
    ])

    return f"""
        SELECT
            loan_id,
            principal_amount_inr
        FROM {table}
        ORDER BY principal_amount_inr DESC
        LIMIT {int(limit)}
    """
