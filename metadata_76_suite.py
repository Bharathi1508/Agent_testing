
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE_URL = "http://127.0.0.1:8000"
BASELINE = Path("metadata_baseline.json")
REPORT_DIR = Path("reports")

GOLD_TABLES = [
    "gold_account_balance_trends",
    "gold_branch_performance",
    "gold_complaint_metrics",
    "gold_customer_360",
    "gold_daily_transaction_analytics",
    "gold_fraud_analysis",
    "gold_kyc_compliance",
    "gold_loan_portfolio_summary",
]


def call_agent(action, table=None, column=None):
    payload = {
        "action": action,
        "table_name": table,
        "column_name": column,
    }
    request = Request(
        BASE_URL + "/metadata/run",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        data = json.load(response)
    if data.get("status") != "success":
        raise RuntimeError(str(data))
    return data["result"]


def capture_baseline():
    tables = call_agent("list_tables")
    found = {r["table_name"] for r in tables}
    missing = set(GOLD_TABLES) - found

    if missing:
        raise RuntimeError(f"Missing Gold tables: {sorted(missing)}")

    columns = {}
    for table in GOLD_TABLES:
        rows = call_agent("get_columns", table)
        columns[table] = {
            r["column_name"]: r["data_type"]
            for r in rows
        }

    baseline = {
        "source": "candidate_snapshot_from_metadata_agent",
        "verified_independently": False,
        "tables": sorted(found),
        "columns": columns,
    }

    BASELINE.write_text(
        json.dumps(baseline, indent=2),
        encoding="utf-8",
    )
    print(f"Candidate baseline saved: {BASELINE}")
    print("Review against Databricks Unity Catalog before approval.")


def execute_suite():
    if not BASELINE.exists():
        raise RuntimeError("Run --capture first.")

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    if not baseline.get("verified_independently"):
        raise RuntimeError(
            "Baseline not independently verified. "
            "Review against Unity Catalog, then set "
            "verified_independently to true."
        )

    tables = baseline["tables"]
    columns = baseline["columns"]
    cases = []

    def add(name, action, table, column, validator, expected):
        cases.append({
            "test_id": f"META_{len(cases) + 1:03d}",
            "name": name,
            "action": action,
            "table": table,
            "column": column,
            "validator": validator,
            "expected": expected,
        })

    # 8 Gold table discovery checks
    for table in GOLD_TABLES:
        add("Table discovery", "list_tables", None, None,
            "table_exists", table)

    # 8 column-list checks
    for table in GOLD_TABLES:
        add("Column discovery", "get_columns", table, None,
            "column_map", columns[table])

    pairs = [
        (table, column)
        for table in GOLD_TABLES
        for column in sorted(columns[table])
    ]

    if len(pairs) < 20:
        raise RuntimeError("At least 20 known columns are required.")

    # 20 existing-column checks
    for table, column in pairs[:20]:
        add("Existing column", "check_column", table, column,
            "column_exists", columns[table][column])

    # 10 nonexistent-column checks
    for i in range(10):
        table = GOLD_TABLES[i % len(GOLD_TABLES)]
        column = f"__heaap_missing_column_{i:03d}__"
        if column in columns[table]:
            raise RuntimeError("Negative test column unexpectedly exists.")
        add("Nonexistent column", "check_column", table, column,
            "column_missing", False)

    # 10 repeatability checks for table discovery
    for _ in range(10):
        add("Table discovery consistency", "list_tables", None, None,
            "table_set", tables)

    # 10 repeatability checks for column discovery
    for i in range(10):
        table = GOLD_TABLES[i % len(GOLD_TABLES)]
        add("Column discovery consistency", "get_columns", table, None,
            "column_map", columns[table])

    # 10 data-type validation checks
    for table, column in pairs[20:30]:
        add("Column data type", "check_column", table, column,
            "column_exists", columns[table][column])

    if len(cases) != 76:
        raise RuntimeError(f"Expected 76 tests, generated {len(cases)}")

    results = []

    for case in cases:
        started = time.perf_counter()
        actual = None
        error = None
        passed = False

        try:
            actual = call_agent(
                case["action"], case["table"], case["column"]
            )
            validator = case["validator"]

            if validator == "table_exists":
                passed = case["expected"] in {
                    row["table_name"] for row in actual
                }

            elif validator == "table_set":
                passed = sorted(
                    row["table_name"] for row in actual
                ) == case["expected"]

            elif validator == "column_map":
                observed = {
                    row["column_name"]: row["data_type"]
                    for row in actual
                }
                passed = observed == case["expected"]

            elif validator == "column_exists":
                passed = (
                    actual.get("exists") is True
                    and actual.get("column", {}).get("data_type")
                    == case["expected"]
                )

            elif validator == "column_missing":
                passed = actual.get("exists") is False

        except Exception as exc:
            error = str(exc)

        duration = round(
            (time.perf_counter() - started) * 1000, 2
        )

        result = {
            **case,
            "passed": passed,
            "actual": actual,
            "error": error,
            "latency_ms": duration,
        }
        results.append(result)

        status = "PASS" if passed else "FAIL"
        print(f"{case['test_id']} | {status} | {case['name']}")

    passed_count = sum(r["passed"] for r in results)

    report = {
        "agent_id": "metadata_agent_001",
        "assurance_type": "functional_metadata_76",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_tests": len(results),
        "passed_tests": passed_count,
        "failed_tests": len(results) - passed_count,
        "status": "passed" if passed_count == 76 else "failed",
        "score": round(passed_count / 76 * 100, 2),
        "baseline": str(BASELINE),
        "results": results,
    }

    REPORT_DIR.mkdir(exist_ok=True)
    output = REPORT_DIR / "metadata_76_actual_results.json"
    output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\nHEAAP METADATA ASSURANCE REPORT")
    print(f"Total tests : {report['total_tests']}")
    print(f"Passed      : {report['passed_tests']}")
    print(f"Failed      : {report['failed_tests']}")
    print(f"Score       : {report['score']}%")
    print(f"Report      : {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    if args.capture:
        capture_baseline()
    elif args.run:
        execute_suite()
    else:
        parser.print_help()
