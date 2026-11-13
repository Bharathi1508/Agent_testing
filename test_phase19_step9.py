"""HEAAP Phase 19.9 - Supervisor assurance integration tests."""

import copy
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.services.dynamic_external_test_planner import (
    generate_dynamic_test_plan,
)
from app.services.persistent_external_assurance_audit import (
    PersistentExternalAssuranceAudit,
)
from app.services.phase19_supervisor_assurance_service import (
    Phase19SupervisorAssuranceService,
    save_phase19_9_result,
)


class TestRegistry:
    def __init__(self, manifest, review_file):
        self.manifest = manifest
        self.review_file = str(Path(review_file).resolve())

    def get_agent(self, agent_id):
        if agent_id != self.manifest["agent_id"]:
            return None

        return {
            "manifest": copy.deepcopy(self.manifest),
            "review_file": self.review_file,
        }


def mock_executor(test, manifest):
    # Simulated response only; no network or SQL execution.
    result = {"status": test["expected_status"]}

    if "expected_error_code" in test:
        result["error_code"] = test["expected_error_code"]

    return result


def main():
    print("HEAAP PHASE 19.9 - SUPERVISOR ASSURANCE")
    print("=" * 55)

    manifest = {
        "agent_id": "synthetic_sql_agent_001",
        "endpoint_name": "synthetic-mock-endpoint",
        "capabilities": [
            "generate_sql",
            "validate_sql",
        ],
    }

    approved_review = {
        "review_id": "synthetic-review-19-9",
        "review_status": "approved",
        "execution_authorized": True,
        "agent": {
            "agent_id": manifest["agent_id"],
            "endpoint_name": manifest["endpoint_name"],
            "declared_capabilities": manifest["capabilities"],
            "manifest_valid": True,
            "capabilities_verified": True,
            "trust_status": "verified",
            "production_approved": False,
        },
    }

    pending_review = copy.deepcopy(approved_review)
    pending_review["review_status"] = "pending_manual_review"
    pending_review["execution_authorized"] = False
    pending_review["agent"]["capabilities_verified"] = False
    pending_review["agent"]["trust_status"] = "unverified"

    plan = generate_dynamic_test_plan(manifest)
    plan["source_review_id"] = approved_review["review_id"]
    plan["source_review_status"] = "approved"

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        review_file = root / "synthetic_review.json"

        registry = TestRegistry(
            manifest,
            review_file,
        )

        audit = PersistentExternalAssuranceAudit(
            root / "audit.db"
        )

        service = Phase19SupervisorAssuranceService(
            registry=registry,
            audit=audit,
            mock_executor=mock_executor,
        )

        # Patch review loading for synthetic tests only.
        loader = (
            "app.services."
            "phase19_supervisor_assurance_service."
            "load_onboarding_review"
        )

        validator = (
            "app.services."
            "phase19_supervisor_assurance_service."
            "validate_onboarding_approval"
        )

        with patch(
            loader,
            return_value=approved_review,
        ), patch(validator) as approval_check:

            result = service.run(
                plan,
                review_file,
                approved_run=True,
            )

            assert result["report"]["verdict"] == "PASS"
            assert result["report"]["passed_tests"] == 4
            assert result["audit_verified"] is True
            approval_check.assert_called()

            print("Approved mock assurance: PASS")
            print("Four capability tests executed: PASS")
            print("Persistent audit verified: PASS")

            saved_file = save_phase19_9_result(
                result,
                root / "reports",
            )

            assert Path(saved_file).is_file()
            print("Assurance report saved: PASS")

            try:
                service.run(
                    plan,
                    review_file,
                    approved_run=False,
                )
            except PermissionError:
                print("Missing run authorization blocked: PASS")
            else:
                raise AssertionError(
                    "Unauthorized mock run was allowed"
                )

        with patch(
            loader,
            return_value=pending_review,
        ):
            pending_plan = copy.deepcopy(plan)
            pending_plan["source_review_status"] = (
                "pending_manual_review"
            )

            try:
                service.run(
                    pending_plan,
                    review_file,
                    approved_run=True,
                )
            except PermissionError:
                print("Pending agent execution blocked: PASS")
            else:
                raise AssertionError(
                    "Pending agent was allowed"
                )

        def failing_mock_executor(test, manifest):
            return {"status": "unexpected"}

        failing_service = Phase19SupervisorAssuranceService(
            registry=registry,
            audit=audit,
            mock_executor=failing_mock_executor,
        )

        with patch(
            loader,
            return_value=approved_review,
        ), patch(validator):
            failed_result = failing_service.run(
                plan,
                review_file,
                approved_run=True,
            )

            assert failed_result["report"]["verdict"] == "FAIL"
            assert failed_result["report"]["failed_tests"] == 4

            print("Failed assurance verdict detected: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 19.9: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
