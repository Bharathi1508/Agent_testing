from datetime import datetime, timezone
from pathlib import Path
import json
import traceback

from app import config
from app.agents.metadata_agent import metadata_agent
from app.services.metadata_service import list_tables, get_columns
from app.services.metadata_validator import validate_metadata


OUTPUT_DIR = Path("reports/dynamic_assurance")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def rows_as_dicts(rows, names):
    """Normalize Databricks tuple, Row or dictionary results."""
    if isinstance(rows, dict):
        rows = rows.get("rows", rows.get("result", rows.get("data", [])))

    if rows is None:
        return []

    result = []

    for row in rows:
        if isinstance(row, dict):
            result.append(dict(row))
        elif hasattr(row, "asDict"):
            result.append(row.asDict())
        elif hasattr(row, "_asdict"):
            result.append(row._asdict())
        else:
            result.append(dict(zip(names, row)))

    return result


def extract_agent_rows(response, names):
    if not isinstance(response, dict):
        raise ValueError("Metadata Agent returned an invalid response")

    if response.get("status") != "success":
        raise ValueError(f"Metadata Agent failed: {response}")

    return rows_as_dicts(response.get("result"), names)


def discover_gold_tables():
    rows = rows_as_dicts(
        list_tables(),
        ["table_name", "table_type"]
    )

    tables = sorted({
        str(row["table_name"])
        for row in rows
        if str(row.get("table_name", "")).startswith("gold_")
    })

    return tables


def test_table(table_name):
    result = {
        "table": table_name,
        "status": "INCONCLUSIVE",
        "column_count": 0,
        "checks": {},
        "error": None,
    }

    try:
        # Invoke the actual existing Metadata Agent.
        agent_response = metadata_agent({
            "action": "get_columns",
            "table_name": table_name,
        })

        agent_columns = extract_agent_rows(
            agent_response,
            ["column_name", "data_type", "comment"]
        )

        # Reference retrieval through the existing metadata service.
        trusted_columns = rows_as_dicts(
            get_columns(table_name),
            ["column_name", "data_type", "comment"]
        )

        result["column_count"] = len(trusted_columns)

        if not trusted_columns:
            result["status"] = "INCONCLUSIVE"
            result["error"] = "No columns returned from catalog"
            return result

        validation = validate_metadata(
            agent_columns,
            trusted_columns
        )

        result["checks"] = validation
        result["status"] = validation["status"]

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = str(exc)

    return result


def run():
    print("Starting Dynamic Gold Metadata Assurance")
    print("Catalog:", config.DATABRICKS_CATALOG)
    print("Schema:", config.DATABRICKS_SCHEMA)

    tables = discover_gold_tables()

    print("Business Gold tables discovered:", len(tables))

    results = []

    for index, table in enumerate(tables, 1):
        print(f"[{index}/{len(tables)}] Testing {table}")

        result = test_table(table)
        results.append(result)

        print("  Status:", result["status"])

    counts = {
        status: sum(r["status"] == status for r in results)
        for status in ("PASS", "FAIL", "INCONCLUSIVE")
    }

    report = {
        "assurance_type": "dynamic_gold_metadata_schema",
        "validation_scope": "table_column_schema_consistency",
        "semantic_relevance_verified": False,
        "reference_independence": "shared_metadata_service",
        "catalog": config.DATABRICKS_CATALOG,
        "schema": config.DATABRICKS_SCHEMA,
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "total_tables": len(tables),
        "passed": counts["PASS"],
        "failed": counts["FAIL"],
        "inconclusive": counts["INCONCLUSIVE"],
        "results": results,
    }

    path = OUTPUT_DIR / "latest_metadata_assurance.json"

    path.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8"
    )

    print("\n" + "=" * 50)
    print("DYNAMIC METADATA ASSURANCE RESULTS")
    print("=" * 50)
    print("Total tables:", report["total_tables"])
    print("Passed:", report["passed"])
    print("Failed:", report["failed"])
    print("Inconclusive:", report["inconclusive"])
    print("Report:", path)

    return report


if __name__ == "__main__":
    try:
        run()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
