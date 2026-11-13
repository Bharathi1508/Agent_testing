"""HEAAP Phase 19.7 - Dynamic external test plan validation."""

from app.services.dynamic_external_test_planner import TEST_TEMPLATES


ALLOWED_STATUSES = {"success", "error", "rejected"}
ALLOWED_TEST_TYPES = {"functional", "adversarial", "security"}


def validate_external_test_plan(plan):
    errors = []

    if not isinstance(plan, dict):
        return {
            "valid": False,
            "errors": ["Test plan must be an object"],
            "validated_tests": 0,
        }

    agent_id = plan.get("agent_id")
    capabilities = plan.get("declared_capabilities")
    tests = plan.get("tests")
    unsupported = plan.get("unsupported_capabilities")

    if not isinstance(agent_id, str) or not agent_id.strip():
        errors.append("Invalid agent ID")

    if (
        not isinstance(capabilities, list)
        or not capabilities
        or not all(isinstance(c, str) and c for c in capabilities)
        or len(capabilities) != len(set(capabilities))
    ):
        errors.append("Invalid declared capabilities")
        capabilities = []

    if not isinstance(tests, list):
        errors.append("Tests must be a list")
        tests = []

    if not isinstance(unsupported, list):
        errors.append("Unsupported capabilities must be a list")
        unsupported = []

    if plan.get("total_tests") != len(tests):
        errors.append("Total test count mismatch")

    if plan.get("plan_status") != "pending_review":
        errors.append("Unexpected test plan status")

    if plan.get("execution_authorized") is not False:
        errors.append("Test plan must not authorize execution")

    if plan.get("production_approved") is not False:
        errors.append("Test plan must not approve production")

    if plan.get("live_endpoint_invoked") is not False:
        errors.append("Unexpected live endpoint invocation flag")

    if (
        len(unsupported) != len(set(unsupported))
        or any(
            not isinstance(c, str) or not c
            for c in unsupported
        )
    ):
        errors.append("Invalid unsupported capabilities")

    expected_unsupported = [
        c for c in capabilities if c not in TEST_TEMPLATES
    ]

    if unsupported != expected_unsupported:
        errors.append("Unsupported capability list mismatch")

    seen_ids = set()
    validated_tests = 0

    for index, test in enumerate(tests):
        prefix = f"Test {index + 1}"

        if not isinstance(test, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        test_id = test.get("test_id")
        capability = test.get("capability")
        payload = test.get("payload")
        status = test.get("expected_status")
        test_type = test.get("test_type")

        if not isinstance(test_id, str) or not test_id:
            errors.append(f"{prefix}: invalid test ID")
        elif test_id in seen_ids:
            errors.append(f"{prefix}: duplicate test ID")
        else:
            seen_ids.add(test_id)

        if capability not in capabilities:
            errors.append(f"{prefix}: undeclared capability")
            continue

        if capability not in TEST_TEMPLATES:
            errors.append(f"{prefix}: no supported test contract")
            continue

        if not isinstance(payload, dict):
            errors.append(f"{prefix}: payload must be an object")
            continue

        if status not in ALLOWED_STATUSES:
            errors.append(f"{prefix}: invalid expected status")
            continue

        if test_type not in ALLOWED_TEST_TYPES:
            errors.append(f"{prefix}: invalid test type")
            continue

        templates = TEST_TEMPLATES[capability]

        matched = any(
            test_id == template["test_id"]
            and payload == template["payload"]
            and status == template["expected_status"]
            and test_type == template["test_type"]
            and test.get("expected_error_code")
                == template.get("expected_error_code")
            for template in templates
        )

        if not matched:
            errors.append(f"{prefix}: test does not match template")
            continue

        validated_tests += 1

    expected_count = sum(
        len(TEST_TEMPLATES[c])
        for c in capabilities
        if c in TEST_TEMPLATES
    )

    if len(tests) != expected_count:
        errors.append("Incomplete capability test coverage")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "validated_tests": validated_tests,
    }
