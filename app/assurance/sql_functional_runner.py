from datetime import datetime, timezone
from app.agents.real_sql_agent import (
    SQL_TEMPLATES,
    run_sql_agent,
)


def run_sql_functional_tests():
    results = []

    # Positive tests: all supported questions
    for question, expected_sql in SQL_TEMPLATES.items():
        response = run_sql_agent(question)

        passed = (
            response.get("status") == "success"
            and response.get("validation_passed") is True
            and response.get("sql_query") == expected_sql
            and response.get("database_executed") is False
        )

        results.append({
            "question": question,
            "test_type": "supported_template",
            "status": "passed" if passed else "failed",
            "expected_sql": expected_sql,
            "actual_sql": response.get("sql_query"),
            "error_code": response.get("error_code"),
        })

    # Negative tests: intentionally unsupported questions
    unsupported_questions = [
        "What is the total outstanding loan amount?",
        "Show overdue loans",
        "Show account balance trends",
    ]

    for question in unsupported_questions:
        response = run_sql_agent(question)

        rejected_correctly = (
            response.get("status") == "rejected"
            and response.get("error_code") == "UNSUPPORTED_QUESTION"
            and not response.get("sql_query")
            and response.get("database_executed") is False
        )

        results.append({
            "question": question,
            "test_type": "unsupported_question_rejection",
            "status": "passed" if rejected_correctly else "failed",
            "expected_behavior": "UNSUPPORTED_QUESTION",
            "actual_sql": response.get("sql_query"),
            "error_code": response.get("error_code"),
        })

    passed = sum(
        result["status"] == "passed"
        for result in results
    )

    return {
        "agent_id": "sql_agent_real_001",
        "assurance_type": "functional_behavior",
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "total_tests": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "score": round(passed / len(results) * 100, 2),
        "database_executed": False,
        "validation_scope": "template_behavior_only",
        "results": results,
    }
