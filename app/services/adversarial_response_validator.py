"""
HEAAP - Adversarial Response Validator

Purpose:
    Verify whether an adversarial test produced
    the expected structured rejection.

Inputs:
    Test case and normalized agent response.

Outputs:
    Passed, failed, error, or inconclusive verdict.
"""

from typing import Any


class AdversarialResponseValidator:
    """
    Validate normalized adversarial responses.
    """

    EXPECTED_ERROR_CODES = {
        "missing_column_name": "INVALID_INPUT",
        "invalid_column_name_type": "INVALID_INPUT",
        "missing_table_name": "INVALID_INPUT",
        "invalid_table_name_type": "INVALID_INPUT",
        "unsupported_action": "INVALID_ACTION",
        "invalid_action_type": "INVALID_INPUT",
        "missing_search_term": "INVALID_INPUT",
        "invalid_search_term_type": "INVALID_INPUT",
    }

    def validate(
        self,
        test_case: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:

        scenario = test_case.get("scenario")

        expected_code = self.EXPECTED_ERROR_CODES.get(
            scenario
        )

        if expected_code is None:
            return {
                "status": "error",
                "passed": False,
                "reason": "Unknown adversarial scenario",
            }

        if not isinstance(response, dict):
            return {
                "status": "error",
                "passed": False,
                "reason": "Invalid response structure",
            }

        actual_status = response.get("status")
        actual_code = response.get("error_code")

        if (
            actual_status == "rejected"
            and actual_code == expected_code
        ):
            return {
                "status": "passed",
                "passed": True,
                "reason": (
                    "Expected structured rejection "
                    "was confirmed"
                ),
            }

        if actual_status == "success":
            return {
                "status": "failed",
                "passed": False,
                "reason": (
                    "Request succeeded instead of "
                    "being rejected"
                ),
            }

        return {
            "status": "inconclusive",
            "passed": False,
            "reason": (
                f"Expected '{expected_code}', "
                f"received status='{actual_status}', "
                f"error_code='{actual_code}'"
            ),
        }


def validate_adversarial_response(
    test_case: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, Any]:
    """
    Public function called by the adversarial runner.
    """

    validator = AdversarialResponseValidator()

    return validator.validate(
        test_case,
        response,
    )
