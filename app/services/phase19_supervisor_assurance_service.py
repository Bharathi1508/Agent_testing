"""HEAAP Phase 19.9 - Governed mock assurance orchestration."""

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.external_agent_approval_gate import (
    load_onboarding_review,
    validate_onboarding_approval,
)
from app.services.external_test_plan_validator import (
    validate_external_test_plan,
)
from app.services.phase19_langgraph_supervisor import (
    run_langgraph_supervisor,
)


class Phase19SupervisorAssuranceService:
    def __init__(self, registry, audit, mock_executor=None):
        self.registry = registry
        self.audit = audit
        self.mock_executor = mock_executor

    def run(self, plan, review_file, *, approved_run=False):
        if not isinstance(plan, dict):
            raise ValueError("Plan must be an object")

        if approved_run is not True:
            raise PermissionError(
                "Separate mock run authorization required"
            )

        # Load current review from the approved review location.
        review = load_onboarding_review(review_file)

        # The supervisor validates the plan and onboarding review.
        supervisor_report = run_langgraph_supervisor(
            plan,
            review,
        )

        decision = supervisor_report["supervisor_decision"]

        if not validate_external_test_plan(plan)["valid"]:
            raise PermissionError("Invalid test plan")

        if decision["decision"] != "ready_for_run_approval":
            raise PermissionError(
                "Supervisor blocked assurance execution"
            )

        agent_id = plan["agent_id"]

        # Require registration in the persistent registry.
        registered = self.registry.get_agent(agent_id)

        if not registered:
            raise PermissionError("Agent is not registered")

        # Recheck the current approval against the registered manifest.
        if not isinstance(registered, dict):
            raise TypeError(
                "Registry get_agent must return a dictionary"
            )

        manifest = registered.get("manifest")

        if not isinstance(manifest, dict):
            raise ValueError(
                "Registry must provide the agent manifest"
            )

        registered_review_file = registered.get("review_file")

        if not isinstance(registered_review_file, str):
            raise ValueError(
                "Registry must provide the review file path"
            )

        if (
            Path(registered_review_file).resolve()
            != Path(review_file).resolve()
        ):
            raise PermissionError(
                "Registered review path mismatch"
            )

        current_review = load_onboarding_review(
            registered_review_file
        )

        validate_onboarding_approval(
            current_review,
            manifest,
        )

        if current_review != review:
            raise PermissionError(
                "Review changed during authorization"
            )

        if plan["declared_capabilities"] != manifest.get(
            "capabilities"
        ):
            raise PermissionError(
                "Registered capability mismatch"
            )

        if plan.get("unsupported_capabilities"):
            raise PermissionError(
                "Unsupported capabilities require test coverage"
            )

        if not plan.get("tests"):
            raise PermissionError(
                "No assurance tests available"
            )

        if self.mock_executor is None:
            raise RuntimeError(
                "No approved mock executor configured"
            )

        # Only a supplied mock executor is allowed.
        test_results = []

        for test in plan["tests"]:
            actual = self.mock_executor(
                copy.deepcopy(test),
                copy.deepcopy(manifest),
            )

            if not isinstance(actual, dict):
                raise TypeError(
                    "Mock executor must return a dictionary"
                )

            actual_status = actual.get("status")
            expected_status = test["expected_status"]

            passed = actual_status == expected_status

            expected_error = test.get("expected_error_code")

            if expected_error is not None:
                passed = (
                    passed
                    and actual.get("error_code") == expected_error
                )

            test_results.append({
                "test_id": test["test_id"],
                "capability": test["capability"],
                "expected_status": expected_status,
                "actual_status": actual_status,
                "passed": passed,
            })

        passed_count = sum(
            result["passed"] for result in test_results
        )

        report = {
            "report_id": uuid.uuid4().hex,
            "phase": "19.9",
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "agent_id": agent_id,
            "plan_id": plan["plan_id"],
            "supervisor_decision": decision["decision"],
            "execution_mode": "mock_only",
            "total_tests": len(test_results),
            "passed_tests": passed_count,
            "failed_tests": len(test_results) - passed_count,
            "verdict": (
                "PASS"
                if passed_count == len(test_results)
                else "FAIL"
            ),
            "results": test_results,
            "governance": {
                "separate_mock_run_authorized": True,
                "live_endpoint_invoked": False,
                "database_executed": False,
                "production_approved": False,
            },
        }

        evidence_id = self.audit.save_report(report)
        audit_verified = self.audit.verify_report(evidence_id)

        if audit_verified is not True:
            raise RuntimeError(
                "Persistent audit verification failed"
            )

        return {
            "report": report,
            "evidence_id": evidence_id,
            "audit_verified": audit_verified,
        }


def save_phase19_9_result(result, output_dir=None):
    if output_dir is None:
        output_dir = Path("reports/phase19_9")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_id = result["report"]["report_id"]
    output_file = output_dir / f"{report_id}.json"

    with output_file.open("x", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    return str(output_file)
