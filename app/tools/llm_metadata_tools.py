
from langchain_core.tools import tool

from app.services.metadata_service import (
    list_tables,
    get_columns,
    check_column,
)


@tool
def list_gold_tables() -> list[dict]:
    """List accessible tables in the configured Gold schema."""
    return list_tables()


@tool
def describe_gold_table(table_name: str) -> list[dict]:
    """Get column names, types and comments for a Gold table."""
    return get_columns(table_name)


@tool
def verify_gold_column(
    table_name: str,
    column_name: str
) -> dict:
    """Check whether a column exists in a Gold table."""
    return check_column(table_name, column_name)


metadata_tools = [
    list_gold_tables,
    describe_gold_table,
    verify_gold_column,
]
from langchain_core.tools import tool
from app.services.metadata_service import search_columns


@tool
def search_gold_columns(column_name: str) -> list[dict]:
    """Search Gold tables for columns matching a name."""
    return search_columns(column_name)