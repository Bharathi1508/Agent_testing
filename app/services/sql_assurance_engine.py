import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import sqlglot
from sqlglot import exp


class SQLAssuranceEngine:

    def __init__(self, output_dir=None):
        self.output_dir = Path(
            output_dir or "reports/phase22_20/sql_assurance"
        )

    def validate(self, sql_text, reference):
        findings = []
        referenced_columns = []
        referenced_tables = []

        def finding(category, message):
            findings.append({
                "category": category,
                "message": message,
            })

        if not isinstance(sql_text, str) or not sql_text.strip():
            finding("invalid_sql", "SQL must be nonempty text")
            return self._report(
                "fail", findings, [], []
            )

        if not isinstance(reference, dict):
            finding("invalid_reference", "Reference must be an object")
            return self._report(
                "inconclusive", findings, [], []
            )

        reference_body = {
            "catalog": reference.get("catalog"),
            "schema": reference.get("schema"),
            "table": reference.get("table"),
            "columns": reference.get("columns"),
        }

        canonical = json.dumps(
            reference_body,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        fingerprint = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        if fingerprint != reference.get("fingerprint"):
            finding(
                "reference_integrity",
                "Trusted reference fingerprint mismatch"
            )
            return self._report(
                "inconclusive", findings, [], []
            )

        try:
            statements = sqlglot.parse(
                sql_text,
                read="databricks",
                error_level="RAISE",
            )
        except Exception as exc:
            finding(
                "sql_parse_error",
                f"SQL parsing failed: {type(exc).__name__}"
            )
            return self._report(
                "fail", findings, [], []
            )

        if len(statements) != 1 or statements[0] is None:
            finding(
                "multiple_statements",
                "Exactly one SQL statement is required"
            )
            return self._report(
                "fail", findings, [], []
            )

        statement = statements[0]

        if not isinstance(statement, exp.Select):
            finding(
                "unsafe_statement",
                "Only SELECT statements are permitted"
            )
            return self._report(
                "fail", findings, [], []
            )

        unsupported_nodes = (
            exp.Join,
            exp.Subquery,
            exp.Union,
            exp.Intersect,
            exp.Except,
            exp.CTE,
            exp.With,
            exp.Command,
            exp.Anonymous,
        )

        if any(
            isinstance(node, unsupported_nodes)
            for node in statement.walk()
        ):
            finding(
                "unsupported_sql",
                "Complex or unsupported SQL structure"
            )
            return self._report(
                "inconclusive", findings, [], []
            )

        if any(
            isinstance(node, exp.Star)
            for node in statement.walk()
        ):
            finding(
                "wildcard_not_allowed",
                "SELECT * is not allowed"
            )
            return self._report(
                "fail", findings, [], []
            )

        tables = list(statement.find_all(exp.Table))

        if len(tables) != 1:
            finding(
                "unsupported_table_scope",
                "Exactly one table is supported"
            )
            return self._report(
                "inconclusive", findings, [], []
            )

        table = tables[0]

        table_name = table.name
        referenced_tables.append(table_name)

        expected_table = reference.get("table")

        if table_name.lower() != str(expected_table).lower():
            finding(
                "incorrect_table",
                f"Expected {expected_table}, got {table_name}"
            )

        expected_schema = reference.get("schema")
        expected_catalog = reference.get("catalog")

        if table.db and table.db.lower() != str(expected_schema).lower():
            finding(
                "incorrect_schema",
                "SQL references an unexpected schema"
            )

        if table.catalog and table.catalog.lower() != str(expected_catalog).lower():
            finding(
                "incorrect_catalog",
                "SQL references an unexpected catalog"
            )

        columns = reference.get("columns")

        if not isinstance(columns, list):
            finding(
                "invalid_reference",
                "Reference columns are not a list"
            )
            return self._report(
                "inconclusive",
                findings,
                referenced_tables,
                [],
            )

        expected_columns = {
            item["column_name"].lower()
            for item in columns
            if isinstance(item, dict)
            and isinstance(item.get("column_name"), str)
        }

        for column in statement.find_all(exp.Column):
            column_name = column.name
            referenced_columns.append(column_name)

            if column_name.lower() not in expected_columns:
                finding(
                    "unknown_column",
                    f"Unknown column: {column_name}"
                )

            if (
                column.table
                and column.table.lower() != table_name.lower()
                and (
                    not table.alias
                    or column.table.lower() != table.alias.lower()
                )
            ):
                finding(
                    "unknown_table_qualifier",
                    f"Unknown table qualifier: {column.table}"
                )

        if findings:
            status = "fail"
        else:
            status = "pass"

        return self._report(
            status,
            findings,
            referenced_tables,
            referenced_columns,
        )

    def _report(
        self,
        status,
        findings,
        referenced_tables,
        referenced_columns,
    ):
        return {
            "validation_id": str(uuid.uuid4()),
            "phase": "22.20",
            "component": "sql_assurance_engine",
            "validated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": status,
            "findings": findings,
            "finding_count": len(findings),
            "referenced_tables": referenced_tables,
            "referenced_columns": referenced_columns,
            "validation_scope": "static_single_table_sql",
            "sql_executed": False,
        }

    def save_report(self, report):
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        validation_id = report["validation_id"]
        uuid.UUID(validation_id)

        path = self.output_dir / (
            f"sql_validation_{validation_id}.json"
        )

        with path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(path)
