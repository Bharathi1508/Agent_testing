"""
HEAAP Phase 22.9 - Local Metadata Test Adapter

A deterministic test double for validating the
execution pipeline. Not a real Metadata Agent.
"""

class LocalMetadataTestAdapter:

    def __init__(self, schema_snapshot):
        if not isinstance(schema_snapshot, dict):
            raise ValueError("Schema snapshot must be an object")

        tables = schema_snapshot.get("tables")

        if not isinstance(tables, dict):
            raise ValueError("Invalid schema snapshot")

        self.tables = tables

    def execute(self, test_case):
        table = test_case.get("table")
        column = test_case.get("column")
        method = test_case.get("validation_method")

        if not isinstance(table, str) or not isinstance(column, str):
            raise ValueError("Missing table or column")

        columns = self.tables.get(table, {})

        if method == "exact_boolean":
            return {
                "exists": column in columns
            }

        if method == "exact_type":
            return {
                "data_type": columns.get(column)
            }

        raise ValueError(
            f"Unsupported validation method: {method}"
        )
