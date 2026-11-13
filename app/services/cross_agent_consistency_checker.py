import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.sql_assurance_engine import (
    SQLAssuranceEngine,
)


class CrossAgentConsistencyChecker:

    def __init__(self, output_dir=None):
        self.sql_engine = SQLAssuranceEngine()
        self.output_dir = Path(
            output_dir or
            "reports/phase22_20/cross_agent"
        )

    def check(
        self,
        *,
        question,
        metadata_response,
        sql_response,
        validator_response,
        trusted_reference,
    ):
        findings = []
        checks = {}

        def add_finding(category, message):
            findings.append({
                "category": category,
                "message": message,
            })

        # 1. Validate input structures.
        if not isinstance(metadata_response, dict):
            raise ValueError(
                "metadata_response must be an object"
            )

        if not isinstance(sql_response, dict):
            raise ValueError(
                "sql_response must be an object"
            )

        if not isinstance(validator_response, dict):
            raise ValueError(
                "validator_response must be an object"
            )

        if not isinstance(trusted_reference, dict):
            raise ValueError(
                "trusted_reference must be an object"
            )

        # 2. Validate metadata against reference.
        expected_table = trusted_reference.get("table")
        metadata_table = metadata_response.get("table")

        checks["metadata_table_match"] = (
            isinstance(metadata_table, str)
            and isinstance(expected_table, str)
            and metadata_table.lower()
            == expected_table.lower()
        )

        if not checks["metadata_table_match"]:
            add_finding(
                "metadata_table_mismatch",
                "Metadata Agent selected an unexpected table",
            )

        reference_columns = trusted_reference.get("columns")

        if not isinstance(reference_columns, list):
            raise ValueError(
                "Trusted reference has invalid columns"
            )

        known_columns = {
            item["column_name"].lower()
            for item in reference_columns
            if isinstance(item, dict)
            and isinstance(item.get("column_name"), str)
        }

        metadata_columns = metadata_response.get("columns")

        if not isinstance(metadata_columns, list):
            raise ValueError(
                "Metadata response columns must be a list"
            )

        selected_columns = set()

        for item in metadata_columns:
            if isinstance(item, str):
                name = item
            elif isinstance(item, dict):
                name = item.get("column_name")
            else:
                name = None

            if not isinstance(name, str):
                add_finding(
                    "invalid_metadata_column",
                    "Metadata contains an invalid column",
                )
                continue

            selected_columns.add(name.lower())

            if name.lower() not in known_columns:
                add_finding(
                    "unknown_metadata_column",
                    f"Unknown metadata column: {name}",
                )

        checks["metadata_columns_valid"] = not any(
            item["category"] in {
                "unknown_metadata_column",
                "invalid_metadata_column",
            }
            for item in findings
        )

        # 3. Independently validate generated SQL.
        sql_text = sql_response.get("sql")

        sql_report = self.sql_engine.validate(
            sql_text,
            trusted_reference,
        )

        checks["sql_assurance_status"] = (
            sql_report["status"]
        )

        if sql_report["status"] != "pass":
            add_finding(
                "sql_assurance_issue",
                "Independent SQL assurance did not pass",
            )

        # 4. Check SQL uses metadata-selected columns.
        sql_columns = {
            name.lower()
            for name in sql_report["referenced_columns"]
        }

        missing_from_metadata = (
            sql_columns - selected_columns
        )

        if missing_from_metadata:
            add_finding(
                "metadata_sql_mismatch",
                "SQL uses columns not selected by Metadata Agent: "
                + ", ".join(sorted(missing_from_metadata)),
            )

        checks["metadata_sql_alignment"] = (
            not missing_from_metadata
        )

        # 5. Compare SQL Validator decision.
        validator_decision = validator_response.get(
            "status"
        )

        if not isinstance(validator_decision, str):
            validator_decision = "unknown"
        else:
            validator_decision = (
                validator_decision.lower()
            )

        checks["validator_decision"] = (
            validator_decision
        )

        if validator_decision not in {
            "pass", "fail", "inconclusive"
        }:
            add_finding(
                "invalid_validator_decision",
                "SQL Validator returned an unknown decision",
            )
        elif validator_decision != sql_report["status"]:
            add_finding(
                "validator_disagreement",
                "SQL Validator disagrees with "
                "independent SQL assurance",
            )

        checks["validator_agreement"] = (
            validator_decision == sql_report["status"]
        )

        # 6. Determine overall consistency.
        if sql_report["status"] == "inconclusive":
            status = "inconclusive"
        elif findings:
            status = "inconsistent"
        else:
            status = "consistent"

        return {
            "consistency_id": str(uuid.uuid4()),
            "phase": "22.20",
            "component": "cross_agent_consistency_checker",
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "question": question,
            "status": status,
            "checks": checks,
            "findings": findings,
            "finding_count": len(findings),
            "independent_sql_report": sql_report,
            "execution_type": "not_executed_by_checker",
            "provenance_verified": False,
        }

    def save_report(self, report):
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        consistency_id = report["consistency_id"]
        uuid.UUID(consistency_id)

        path = self.output_dir / (
            f"consistency_{consistency_id}.json"
        )

        with path.open("x", encoding="utf-8") as file:
            json.dump(report, file, indent=2)

        return str(path)
