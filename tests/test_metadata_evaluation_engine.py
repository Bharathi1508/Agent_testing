from app.services.metadata_evaluation_engine import evaluate_metadata


SCHEMA = {
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

EXPECTED = {
    "primary_table": "gold_loan_portfolio_summary",
    "required_columns": [
        "customer_id",
        "loan_id",
        "overdue_installments",
    ],
}


def test_correct_metadata():
    selection = {
        "primary_table": "gold_loan_portfolio_summary",
        "selected_columns": EXPECTED["required_columns"],
    }

    result = evaluate_metadata(selection, EXPECTED, SCHEMA)

    assert result["validation_status"] == "PASS"
    assert result["checks"]["table_correct"] == "PASS"


def test_incorrect_table():
    selection = {
        "primary_table": "gold_account_balance_trends",
        "selected_columns": [
            "account_id",
            "closing_balance_inr",
        ],
    }

    result = evaluate_metadata(selection, EXPECTED, SCHEMA)

    assert result["validation_status"] == "FAIL"
    assert result["checks"]["table_correct"] == "FAIL"


def test_missing_required_column():
    selection = {
        "primary_table": "gold_loan_portfolio_summary",
        "selected_columns": [
            "customer_id",
            "loan_id",
        ],
    }

    result = evaluate_metadata(selection, EXPECTED, SCHEMA)

    assert result["validation_status"] == "FAIL"
    assert "overdue_installments" in result["missing_columns"]


def test_nonexistent_column():
    selection = {
        "primary_table": "gold_loan_portfolio_summary",
        "selected_columns": [
            "customer_id",
            "loan_id",
            "overdue_installments",
            "fake_column",
        ],
    }

    result = evaluate_metadata(selection, EXPECTED, SCHEMA)

    assert result["validation_status"] == "FAIL"
    assert "fake_column" in result["invalid_columns"]


def test_extra_columns_trigger_review():
    selection = {
        "primary_table": "gold_loan_portfolio_summary",
        "selected_columns": [
            "customer_id",
            "loan_id",
            "overdue_installments",
            "loan_status",
        ],
    }

    result = evaluate_metadata(selection, EXPECTED, SCHEMA)

    assert result["validation_status"] == "REVIEW"
    assert "loan_status" in result["extra_columns"]
