import os
from dotenv import load_dotenv
load_dotenv()
import json
import sys
from pathlib import Path
from databricks import sql

BASELINE = Path("metadata_baseline.json")
CATALOG = os.getenv("HEAAP_CATALOG", "")
SCHEMA = os.getenv("HEAAP_SCHEMA", "gold")

TABLES = [
    "gold_account_balance_trends",
    "gold_branch_performance",
    "gold_complaint_metrics",
    "gold_customer_360",
    "gold_daily_transaction_analytics",
    "gold_fraud_analysis",
    "gold_kyc_compliance",
    "gold_loan_portfolio_summary",
]

def normalize_type(value):
    value = str(value).upper().strip()
    return {
        "LONG": "BIGINT",
        "INTEGER": "INT",
        "SHORT": "SMALLINT",
        "BYTE": "TINYINT",
        "BOOL": "BOOLEAN",
    }.get(value, value)

if not BASELINE.exists():
    sys.exit("Baseline missing. Run: python metadata_76_suite.py --capture")

required = [
    "DATABRICKS_SERVER_HOSTNAME",
    "DATABRICKS_HTTP_PATH",
    "DATABRICKS_TOKEN",
]

missing = [name for name in required if not os.getenv(name)]

if missing:
    sys.exit("Missing Databricks variables: " + ", ".join(missing))

if not CATALOG:
    sys.exit("Set HEAAP_CATALOG to your actual Unity Catalog name.")

baseline = json.loads(BASELINE.read_text(encoding="utf-8-sig"))

print("Connecting to Databricks...")

connection = sql.connect(
    server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
    http_path=os.environ["DATABRICKS_HTTP_PATH"],
    access_token=os.environ["DATABRICKS_TOKEN"],
)

actual = {}
comparison = []

try:
    with connection.cursor() as cursor:
        for table in TABLES:
            query = (
                f"SELECT column_name, data_type "
                f"FROM `{CATALOG}`.information_schema.columns "
                f"WHERE table_schema = ? AND table_name = ? "
                f"ORDER BY ordinal_position"
            )

            cursor.execute(query, (SCHEMA, table))
            rows = cursor.fetchall()

            actual[table] = {
                row[0]: str(row[1]).upper()
                for row in rows
            }

            expected = baseline["columns"].get(table, {})

            expected_normalized = {
                key: normalize_type(value)
                for key, value in expected.items()
            }

            actual_normalized = {
                key: normalize_type(value)
                for key, value in actual[table].items()
            }

            matched = (
                len(actual_normalized) > 0
                and expected_normalized == actual_normalized
            )

            comparison.append({
                "table": table,
                "expected_columns": len(expected),
                "actual_columns": len(actual[table]),
                "matched": matched,
                "missing_columns": sorted(
                    set(expected) - set(actual[table])
                ),
                "unexpected_columns": sorted(
                    set(actual[table]) - set(expected)
                ),
                "type_mismatches": {
                    col: {
                        "expected": expected_normalized[col],
                        "actual": actual_normalized[col]
                    }
                    for col in set(expected) & set(actual[table])
                    if expected_normalized[col] != actual_normalized[col]
                }
            })

finally:
    connection.close()

all_matched = all(item["matched"] for item in comparison)

output = {
    "catalog": CATALOG,
    "schema": SCHEMA,
    "verified": all_matched,
    "comparison": comparison
}

Path("metadata_verification_report.json").write_text(
    json.dumps(output, indent=2),
    encoding="utf-8"
)

for item in comparison:
    status = "MATCH" if item["matched"] else "MISMATCH"
    print(
        f"{status:8} {item['table']:38} "
        f"baseline={item['expected_columns']:3} "
        f"databricks={item['actual_columns']:3}"
    )

if all_matched:
    baseline["verified_independently"] = True
    BASELINE.write_text(
        json.dumps(baseline, indent=2),
        encoding="utf-8"
    )
    print("\nSUCCESS: Baseline independently verified.")
else:
    baseline["verified_independently"] = False
    BASELINE.write_text(
        json.dumps(baseline, indent=2),
        encoding="utf-8"
    )
    print("\nVerification failed. Review metadata_verification_report.json.")
    sys.exit(1)
