
"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Phase 13 - Step 7
Dynamic Functional Test Runner

Features:
1. Generate test cases from registered capabilities.
2. Verify agent registration.
3. Verify agent activation and governance approval.
4. Execute agents through Dynamic Supervisor.
5. Validate capability-specific responses.
6. Generate consolidated functional test reports.

Security:
- Active and approved agents only.
- Inactive agents require a separate sandbox runner.
- No automatic agent activation.
- No governance approval bypass.
"""

import logging
import time

from datetime import datetime, timezone
from typing import Any

from app.registry.agent_registry import (
    get_registered_agent,
)

from app.governance.approval_service import (
    is_approved,
)

from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
)

from app.services.test_case_generator import (
    generate_agent_test_cases,
)


logger = logging.getLogger(__name__)


# =====================================================
# RESPONSE VALIDATOR
# =====================================================

class ResponseValidator:
    """
    Validates actual agent responses against
    dynamically generated test contracts.
    """

    @staticmethod
    def validate(
        response: Any,
        test_case: dict[str, Any],
    ) -> dict[str, Any]:

        errors = []

        # ---------------------------------------------
        # 1. Validate response structure
        # ---------------------------------------------

        if not isinstance(response, dict):
            return {
                "passed": False,
                "errors": [
                    "Agent response must be a dictionary."
                ],
            }

        # ---------------------------------------------
        # 2. Validate required response keys
        # ---------------------------------------------

        expected_keys = test_case.get(
            "expected_keys", []
        )

        for key in expected_keys:
            if key not in response:
                errors.append(
                    f"Missing response key: {key}"
                )

        # ---------------------------------------------
        # 3. Validate response status
        # ---------------------------------------------

        expected_status = test_case.get(
            "expected_status", "success"
        )

        if response.get("status") != expected_status:
            errors.append(
                "Unexpected agent response status. "
                f"Expected '{expected_status}', "
                f"received '{response.get('status')}'."
            )

        # ---------------------------------------------
        # 4. Validate action, if present
        # ---------------------------------------------

        expected_action = test_case.get(
            "input", {}
        ).get("action")

        if (
            "action" in response
            and expected_action is not None
            and response["action"] != expected_action
        ):
            errors.append(
                "Agent response action does not "
                "match the requested capability."
            )

        # ---------------------------------------------
        # 5. Validate result type
        # ---------------------------------------------

        result = response.get("result")

        expected_type = test_case.get(
            "result_type"
        )

        if expected_type == "list":

            if not isinstance(result, list):
                errors.append(
                    "Expected result to be a list."
                )

            else:
                required_keys = test_case.get(
                    "required_item_keys", []
                )

                for index, item in enumerate(result):

                    if not isinstance(item, dict):
                        errors.append(
                            f"Result item {index} "
                            "must be a dictionary."
                        )
                        continue

                    for key in required_keys:

                        if key not in item:
                            errors.append(
                                f"Result item {index} "
                                f"is missing '{key}'."
                            )

                # Validate known metadata fields
                if expected_action == "list_tables":
                    for index, item in enumerate(result):
                        if not isinstance(item, dict):
                            continue

                        for field in (
                            "table_name",
                            "table_type",
                        ):
                            if (
                                field in item
                                and not isinstance(
                                    item[field], str
                                )
                            ):
                                errors.append(
                                    f"Item {index}: "
                                    f"'{field}' must be a string."
                                )

                elif expected_action in (
                    "get_columns",
                    "search_columns",
                ):
                    for index, item in enumerate(result):
                        if not isinstance(item, dict):
                            continue

                        for field in (
                            "column_name",
                            "data_type",
                        ):
                            if (
                                field in item
                                and not isinstance(
                                    item[field], str
                                )
                            ):
                                errors.append(
                                    f"Item {index}: "
                                    f"'{field}' must be a string."
                                )

        elif expected_type == "dict":

            if not isinstance(result, dict):
                errors.append(
                    "Expected result to be a dictionary."
                )

            else:
                ResponseValidator._validate_dict_result(
                    result=result,
                    test_case=test_case,
                    errors=errors,
                )

        elif expected_type is not None:
            errors.append(
                f"Unsupported test result type: "
                f"{expected_type}"
            )

        return {
            "passed": len(errors) == 0,
            "errors": errors,
        }

    @staticmethod
    def _validate_dict_result(
        result: dict[str, Any],
        test_case: dict[str, Any],
        errors: list[str],
    ) -> None:

        capability = test_case.get("capability")

        # ---------------------------------------------
        # CHECK COLUMN VALIDATION
        # ---------------------------------------------

        if capability == "check_column":

            if "exists" not in result:
                errors.append(
                    "Missing 'exists' field."
                )
                return

            if not isinstance(result["exists"], bool):
                errors.append(
                    "'exists' must be a boolean."
                )
                return

            expected_exists = test_case.get(
                "expected_exists"
            )

            if (
                expected_exists is not None
                and result["exists"] != expected_exists
            ):
                errors.append(
                    "Column existence result mismatch. "
                    f"Expected {expected_exists}, "
                    f"received {result['exists']}."
                )

            expected_column = test_case.get(
                "expected_column_name"
            )

            if result["exists"] is True:

                column = result.get("column")

                if not isinstance(column, dict):
                    errors.append(
                        "Expected column metadata "
                        "dictionary."
                    )
                    return

                actual_name = column.get(
                    "column_name"
                )

                if not isinstance(actual_name, str):
                    errors.append(
                        "Column metadata must contain "
                        "a string column_name."
                    )

                elif (
                    expected_column is not None
                    and actual_name.lower()
                    != expected_column.lower()
                ):
                    errors.append(
                        "Returned column name does "
                        "not match expected column."
                    )

                if not isinstance(
                    column.get("data_type"), str
                ):
                    errors.append(
                        "Column metadata must contain "
                        "a string data_type."
                    )

            else:
                if "column_name" not in result:
                    errors.append(
                        "Missing column_name for "
                        "nonexistent column."
                    )

        # Additional capability-specific dictionary
        # validators can be added here.


# =====================================================
# DYNAMIC TEST RUNNER
# =====================================================

class DynamicTestRunner:
    """
    Runs functional tests for registered,
    active, governance-approved agents.
    """

    def __init__(self):

        self.validator = ResponseValidator()

    # -------------------------------------------------
    # EXECUTE ONE TEST CASE
    # -------------------------------------------------

    def run_test_case(
        self,
        agent_id: str,
        test_case: dict[str, Any],
    ) -> dict[str, Any]:

        started = time.perf_counter()

        test_id = test_case.get(
            "test_id", "unknown_test"
        )

        capability = test_case.get(
            "capability", ""
        )

        try:

            # -----------------------------------------
            # 1. Verify agent registration
            # -----------------------------------------

            manifest = get_registered_agent(
                agent_id
            )

            if manifest is None:
                raise PermissionError(
                    "Agent is not registered."
                )

            # -----------------------------------------
            # 2. Verify agent status
            # -----------------------------------------

            if manifest.status != "active":
                raise PermissionError(
                    "Agent is inactive. "
                    "Use an authorized sandbox "
                    "assurance executor."
                )

            # -----------------------------------------
            # 3. Verify governance approval
            # -----------------------------------------

            if not is_approved(manifest):
                raise PermissionError(
                    "Agent is not governance-approved."
                )

            # -----------------------------------------
            # 4. Verify declared capability
            # -----------------------------------------

            declared_capabilities = {
                str(item).strip().lower()
                for item in manifest.capabilities
            }

            capability = str(
                capability
            ).strip().lower()

            if capability not in declared_capabilities:
                raise PermissionError(
                    "Capability is not declared "
                    "by the registered agent."
                )

            # -----------------------------------------
            # 5. Validate test input
            # -----------------------------------------

            payload = test_case.get(
                "input"
            )

            if not isinstance(payload, dict):
                raise ValueError(
                    "Test input must be a dictionary."
                )

            if payload.get("action") != capability:
                raise ValueError(
                    "Test action must match capability."
                )

            # -----------------------------------------
            # 6. Execute through Dynamic Supervisor
            # -----------------------------------------

            supervisor_response = (
                execute_supervisor_request(
                    capability=capability,
                    payload=payload,
                    preferred_agent_id=agent_id,
                )
            )

            # -----------------------------------------
            # 7. Verify supervisor response
            # -----------------------------------------

            if not isinstance(
                supervisor_response, dict
            ):
                raise RuntimeError(
                    "Supervisor returned invalid response."
                )

            if (
                supervisor_response.get("status")
                != "success"
            ):
                raise RuntimeError(
                    "Supervisor execution unsuccessful."
                )

            selected_agent = (
                supervisor_response.get(
                    "selected_agent"
                )
            )

            if selected_agent != agent_id:
                raise RuntimeError(
                    "Supervisor selected an "
                    "unexpected agent."
                )

            # -----------------------------------------
            # 8. Extract actual agent response
            # -----------------------------------------

            agent_response = (
                supervisor_response.get(
                    "result"
                )
            )

            # -----------------------------------------
            # 9. Validate response
            # -----------------------------------------

            validation = (
                self.validator.validate(
                    response=agent_response,
                    test_case=test_case,
                )
            )

            passed = validation["passed"]

            status = (
                "passed"
                if passed
                else "failed"
            )

            # -----------------------------------------
            # 10. Return test result
            # -----------------------------------------

            return {
                "test_id": test_id,
                "agent_id": agent_id,
                "capability": capability,
                "status": status,
                "passed": passed,
                "errors": validation["errors"],
                "execution_time_ms": round(
                    (
                        time.perf_counter()
                        - started
                    ) * 1000,
                    2,
                ),
                "tested_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

        except PermissionError as exc:

            return self._error_result(
                test_id,
                agent_id,
                capability,
                "blocked",
                str(exc),
                started,
            )

        except Exception as exc:

            logger.exception(
                "Dynamic functional test failed: %s",
                test_id,
            )

            return self._error_result(
                test_id,
                agent_id,
                capability,
                "error",
                f"{type(exc).__name__}: {exc}",
                started,
            )

    # -------------------------------------------------
    # STANDARD ERROR RESULT
    # -------------------------------------------------

    @staticmethod
    def _error_result(
        test_id,
        agent_id,
        capability,
        status,
        error,
        started,
    ):

        return {
            "test_id": test_id,
            "agent_id": agent_id,
            "capability": capability,
            "status": status,
            "passed": False,
            "errors": [error],
            "execution_time_ms": round(
                (
                    time.perf_counter()
                    - started
                ) * 1000,
                2,
            ),
            "tested_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    # -------------------------------------------------
    # EXECUTE ALL GENERATED TEST CASES
    # -------------------------------------------------

    def run_agent_tests(
        self,
        agent_id: str,
    ) -> dict[str, Any]:

        generated = generate_agent_test_cases(
            agent_id
        )

        test_cases = generated.get(
            "test_cases", []
        )

        results = []

        for test_case in test_cases:

            result = self.run_test_case(
                agent_id=agent_id,
                test_case=test_case,
            )

            results.append(result)

        # ---------------------------------------------
        # CALCULATE SUMMARY
        # ---------------------------------------------

        passed = sum(
            1 for result in results
            if result["status"] == "passed"
        )

        failed = sum(
            1 for result in results
            if result["status"] == "failed"
        )

        errors = sum(
            1 for result in results
            if result["status"] == "error"
        )

        blocked = sum(
            1 for result in results
            if result["status"] == "blocked"
        )

        total = len(results)

        unsupported = generated.get(
            "unsupported_capabilities", []
        )

        overall_passed = (
            generated.get("status") == "generated"
            and total > 0
            and passed == total
            and len(unsupported) == 0
        )

        if overall_passed:
            overall_status = "passed"

        elif unsupported or total == 0:
            overall_status = "incomplete"

        else:
            overall_status = "failed"

        # ---------------------------------------------
        # CONSOLIDATED TEST REPORT
        # ---------------------------------------------

        return {
            "agent_id": agent_id,
            "status": overall_status,
            "passed": overall_passed,
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": failed,
            "error_tests": errors,
            "blocked_tests": blocked,
            "unsupported_capabilities": unsupported,
            "results": results,
        }


# =====================================================
# PUBLIC ENTRY POINT
# =====================================================

def run_dynamic_agent_tests(
    agent_id: str,
) -> dict[str, Any]:

    runner = DynamicTestRunner()

    return runner.run_agent_tests(
        agent_id=agent_id
    )
