from app.services.metadata_test_fixture_loader import (
    load_metadata_test_cases,
)


def build_metadata_agent_tests():
    """Convert trusted metadata fixtures into runner test cases."""

    fixtures = load_metadata_test_cases()
    tests = []

    for fixture in fixtures:
        expected = fixture["expected"]["column_exists"]
        column_name = fixture["input"]["column_name"]

        tests.append({
            "test_id": fixture["test_id"],
            "capability": fixture["capability"],
            "input": dict(fixture["input"]),
            "expected_status": "success",
            "result_type": "dict",
            "expected_exists": expected,
            "expected_column_name": (
                column_name if expected else None
            ),
        })

    return tests
