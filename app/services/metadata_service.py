from app.config import (
    DATABRICKS_CATALOG,
    DATABRICKS_SCHEMA,
)
from app.adapters.databricks_client import execute_query


def list_tables():
    query = """
        SELECT table_name, table_type
        FROM system.information_schema.tables
        WHERE table_catalog = ?
          AND table_schema = ?
        ORDER BY table_name
    """

    return execute_query(
        query,
        [DATABRICKS_CATALOG, DATABRICKS_SCHEMA]
    )


def get_columns(table_name):
    query = """
        SELECT column_name, data_type, comment
        FROM system.information_schema.columns
        WHERE table_catalog = ?
          AND table_schema = ?
          AND table_name = ?
        ORDER BY ordinal_position
    """

    return execute_query(
        query,
        [DATABRICKS_CATALOG, DATABRICKS_SCHEMA, table_name]
    )


def check_column(table_name, column_name):
    columns = get_columns(table_name)

    for column in columns:
        if column["column_name"].lower() == column_name.lower():
            return {"exists": True, "column": column}

    return {"exists": False, "column_name": column_name}

def search_columns(column_name: str):
    """
    Search for a column across all accessible
    tables in the configured Gold schema.
    """

    query = """
        SELECT
            table_name,
            column_name,
            data_type,
            comment
        FROM system.information_schema.columns
        WHERE table_catalog = ?
          AND table_schema = ?
          AND LOWER(column_name) LIKE ?
        ORDER BY table_name, column_name
        LIMIT 100
    """

    return execute_query(
        query,
        [
            DATABRICKS_CATALOG,
            DATABRICKS_SCHEMA,
            f"%{column_name.lower()}%"
        ]
    )
