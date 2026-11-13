def metadata_agent(*, question, test_case):
    if test_case.get("scenario") == "metadata_mismatch":
        return {
            "table": "gold_loan_portfolio_summary",
            "columns": ["loan_status"],
        }

    return {
        "table": "gold_loan_portfolio_summary",
        "columns": [
            "loan_status",
            "total_due_inr",
        ],
    }


def sql_agent(*, question, metadata, test_case):
    if test_case.get("scenario") == "bad_sql":
        return {
            "sql": """
                SELECT SUM(customer_salary_inr)
                FROM gold_loan_portfolio_summary
            """
        }

    if test_case.get("scenario") == "metadata_mismatch":
        return {
            "sql": """
                SELECT SUM(total_due_inr)
                FROM gold_loan_portfolio_summary
                WHERE loan_status = 'Active'
            """
        }

    return {
        "sql": """
            SELECT SUM(total_due_inr)
            FROM gold_loan_portfolio_summary
            WHERE loan_status = 'Active'
        """
    }


def sql_validator_agent(*, sql, test_case):
    if test_case.get("scenario") == "bad_sql":
        return {"status": "pass"}

    return {"status": "pass"}


AGENT_ADAPTERS = {
    "metadata_agent": metadata_agent,
    "sql_agent": sql_agent,
    "sql_validator_agent": sql_validator_agent,
}
