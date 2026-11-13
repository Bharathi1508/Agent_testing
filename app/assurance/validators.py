
def validate_response(response, test_case):
    errors = []

    if not isinstance(response, dict):
        return {
            "passed": False,
            "errors": ["Response must be a dictionary"]
        }

    for key in test_case.get("required_keys", []):
        if key not in response:
            errors.append(f"Missing required key: {key}")

    expected_status = test_case.get("expected_status")

    if expected_status is not None:
        if response.get("status") != expected_status:
            errors.append(
                f"Expected status '{expected_status}', "
                f"got '{response.get('status')}'"
            )
    elif response.get("status") != "success":
        errors.append("Expected successful response")

    return {
        "passed": len(errors) == 0,
        "errors": errors
    }
