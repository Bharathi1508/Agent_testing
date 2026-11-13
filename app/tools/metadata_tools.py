from app.services.metadata_service import (
    list_tables,
    get_columns,
    check_column,
)


def list_tables_tool():
    return list_tables()


def get_columns_tool(table_name):
    return get_columns(table_name)


def check_column_tool(table_name, column_name):
    return check_column(table_name, column_name)
from app.services.metadata_service import search_columns


def search_columns_tool(column_name: str):
    return search_columns(column_name)