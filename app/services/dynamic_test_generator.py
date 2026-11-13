"""
HEAAP Phase 22.8 - Dynamic Test Generator

Generates deterministic metadata test cases from
trusted schema snapshots.

No agent invocation, SQL execution, or approval changes.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class DynamicTestGenerator:

    def __init__(self, output_dir="reports/phase22_8"):
        self.output_dir = Path(output_dir)

    @staticmethod
    def _test_id(payload):
        content = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()[:16]

    def generate_metadata_tests(
        self,
        agent_id,
        schema_snapshot,
        limit=1000,
    ):
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("Valid agent_id required")

        if not isinstance(limit, int) or isinstance(limit, bool):
            raise ValueError("Limit must be an integer")

        if not 1 <= limit <= 10000:
            raise ValueError("Limit must be between 1 and 10000")

        if not isinstance(schema_snapshot, dict):
            raise ValueError("Schema snapshot must be an object")

        source = schema_snapshot.get("source")
        tables = schema_snapshot.get("tables")

        if not isinstance(source, str) or not source.strip():
            raise ValueError("Trusted source identifier required")

        if not isinstance(tables, dict) or not tables:
            raise ValueError("Nonempty tables mapping required")

        tests = []

        for table_name, columns in sorted(tables.items()):
            if not isinstance(table_name, str) or not table_name:
                raise ValueError("Invalid table name")

            if not isinstance(columns, dict):
                raise ValueError("Columns must be a mapping")

            for column_name, data_type in sorted(columns.items()):
                if (
                    not isinstance(column_name, str)
                    or not column_name
                    or not isinstance(data_type, str)
                    or not data_type
                ):
                    raise ValueError("Invalid column definition")

                candidates = [
                    {
                        "agent_id": agent_id,
                        "capability": "metadata_search",
                        "question": (
                            f"Does table {table_name} contain "
                            f"column {column_name}?"
                        ),
                        "expected_result": {
                            "exists": True,
                        },
                        "validation_method": "exact_boolean",
                        "source": source,
                        "table": table_name,
                        "column": column_name,
                    },
                    {
                        "agent_id": agent_id,
                        "capability": "schema_discovery",
                        "question": (
                            f"What is the data type of "
                            f"{table_name}.{column_name}?"
                        ),
                        "expected_result": {
                            "data_type": data_type,
                        },
                        "validation_method": "exact_type",
                        "source": source,
                        "table": table_name,
                        "column": column_name,
                    },
                ]

                for candidate in candidates:
                    candidate["test_id"] = self._test_id(candidate)
                    tests.append(candidate)

                    if len(tests) >= limit:
                        return tests

        return tests

    def save_tests(self, agent_id, tests):
        if not isinstance(tests, list):
            raise ValueError("Tests must be a list")

        self.output_dir.mkdir(
            parents=True, exist_ok=True
        )

        payload = {
            "agent_id": agent_id,
            "phase": "22.8",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total_tests": len(tests),
            "tests": tests,
        }

        # Unique content-derived filename avoids unsafe agent IDs
        # in output paths.
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]

        output_file = self.output_dir / (
            f"generated_tests_{digest}.json"
        )

        with output_file.open("x", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        return str(output_file)
