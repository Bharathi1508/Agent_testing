from datetime import datetime, timezone

from app.services.metadata_evaluation_engine import evaluate_metadata


def run_negative_metadata_tests():
    expected = {
        "primary_table": "gold_loan_portfolio_summary",
        "required_columns": [
            "customer_id",
            "loan_id",
            "overdue_installments",
        ],
    }

    # Controlled fixture based on known HEAAP Gold columns.
    # This is not a live Databricks schema fetch.
    schema = {
        "gold_loan_portfolio_summary": [
            "customer_id",
            "loan_id",
            "overdue_installments",
            "loan_status",
        ],
        "gold_account_balance_trends": [
            "account_id",
            "closing_balance_inr",
        ],
    }

    cases = [
        {
            "name": "correct_metadata",
            "expected_status": "PASS",
            "selection": {
                "primary_table": "gold_loan_portfolio_summary",
                "selected_columns": [
                    "customer_id",
                    "loan_id",
                    "overdue_installments",
                ],
            },
        },
        {
            "name": "incorrect_table",
            "expected_status": "FAIL",
            "selection": {
                "primary_table": "gold_account_balance_trends",
                "selected_columns": [
                    "account_id",
                    "closing_balance_inr",
                ],
            },
        },
        {
            "name": "missing_required_column",
            "expected_status": "FAIL",
            "selection": {
                "primary_table": "gold_loan_portfolio_summary",
                "selected_columns": [
                    "customer_id",
                    "loan_id",
                ],
            },
        },
        {
            "name": "nonexistent_column",
            "expected_status": "FAIL",
            "selection": {
                "primary_table": "gold_loan_portfolio_summary",
                "selected_columns": [
                    "customer_id",
                    "loan_id",
                    "overdue_installments",
                    "fake_column",
                ],
            },
        },
        {
            "name": "extra_column",
            "expected_status": "REVIEW",
            "selection": {
                "primary_table": "gold_loan_portfolio_summary",
                "selected_columns": [
                    "customer_id",
                    "loan_id",
                    "overdue_installments",
                    "loan_status",
                ],
            },
        },
    ]

    results = []

    for case in cases:
        evaluation = evaluate_metadata(
            selection=case["selection"],
            expected=expected,
            live_schema=schema,
        )

        actual_status = evaluation["validation_status"]

        results.append({
            "test_name": case["name"],
            "expected_status": case["expected_status"],
            "actual_status": actual_status,
            "test_passed": actual_status == case["expected_status"],
            "evaluation": evaluation,
        })

    passed = sum(r["test_passed"] for r in results)

    return {
        "suite": "HEAAP_METADATA_NEGATIVE_TESTING",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_tests": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "all_tests_passed": passed == len(results),
        "schema_source": "CONTROLLED_TEST_FIXTURE",
        "live_databricks_verified": False,
        "results": results,
    }
