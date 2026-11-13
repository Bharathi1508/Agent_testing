from pathlib import Path
import json

FIXTURE_PATH = Path(
    "tests/fixtures/metadata_agent_cases.json"
)

def load_metadata_test_cases():
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(
            f"Fixture not found: {FIXTURE_PATH}"
        )

    with FIXTURE_PATH.open("r", encoding="utf-8") as file:
        fixture = json.load(file)

    if fixture.get("agent_id") != "metadata_agent_001":
        raise ValueError("Unexpected fixture agent ID")

    cases = fixture.get("test_cases")

    if not isinstance(cases, list) or not cases:
        raise ValueError("No metadata test cases found")

    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Invalid test case")

        if not all(
            key in case
            for key in ("test_id", "capability", "input", "expected")
        ):
            raise ValueError("Missing required test-case fields")

        if case["capability"] != "check_column":
            raise ValueError("Unsupported fixture capability")

        payload = case["input"]

        if not isinstance(payload, dict):
            raise ValueError("Invalid test input")

        if payload.get("action") != "check_column":
            raise ValueError("Action mismatch")

        if not isinstance(payload.get("table_name"), str):
            raise ValueError("Missing table name")

        if not isinstance(payload.get("column_name"), str):
            raise ValueError("Missing column name")

        expected = case["expected"]

        if (
            not isinstance(expected, dict)
            or type(expected.get("column_exists")) is not bool
        ):
            raise ValueError("Invalid expected column existence")

    return cases
