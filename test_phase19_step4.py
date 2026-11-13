"""HEAAP Phase 19.4 - Persistent registry and audit tests."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.services.persistent_external_agent_registry import (
    PersistentExternalAgentRegistry,
)
from app.services.persistent_external_assurance_audit import (
    PersistentExternalAssuranceAudit,
)
from app.services.phase19_persistent_assurance_service import (
    Phase19PersistentAssuranceService,
)


MANIFEST = {
    "agent_id": "external_sql_agent_001",
    "endpoint_name": "heaap-sql-agent",
    "capabilities": ["generate_sql", "validate_sql"],
}

TESTS = [
    {
        "test_id": "EXT001",
        "capability": "generate_sql",
        "payload": {"question": "total annual premium"},
        "expected_status": "success",
    },
    {
        "test_id": "EXT002",
        "capability": "generate_sql",
        "payload": {"question": "delete all policies"},
        "expected_status": "rejected",
        "expected_error_code": "UNSUPPORTED_QUESTION",
    },
]


def make_review(approved=True):
    return {
        "agent": {
            "agent_id": MANIFEST["agent_id"],
            "endpoint_name": MANIFEST["endpoint_name"],
            "declared_capabilities": MANIFEST["capabilities"],
            "manifest_valid": True,
            "capabilities_verified": approved,
            "trust_status": (
                "verified" if approved else "unverified"
            ),
            "production_approved": False,
        },
        "discovered_endpoint": {
            "provider": "databricks",
            "endpoint_name": MANIFEST["endpoint_name"],
        },
        "review_status": (
            "approved" if approved else "pending_manual_review"
        ),
        "execution_authorized": approved,
        "production_approved": False,
    }


def main():
    print("HEAAP PHASE 19.4 - PERSISTENT REGISTRY AND AUDIT")
    print("=" * 55)

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        registry_path = root / "registry.db"
        audit_path = root / "audit.db"
        review_file = root / "review.json"

        registry = PersistentExternalAgentRegistry(registry_path)
        audit = PersistentExternalAssuranceAudit(audit_path)

        # Synthetic review loader for isolated local testing.
        current_review = make_review(approved=True)

        with patch(
            "app.services.persistent_external_agent_registry."
            "load_onboarding_review",
            side_effect=lambda _: current_review,
        ):
            registry.register_agent(MANIFEST, review_file)

            assert registry.list_agents() == [
                "external_sql_agent_001"
            ]

            print("Persistent agent registration: PASS")

            # Reopen registry to verify persistence.
            reopened_registry = PersistentExternalAgentRegistry(
                registry_path
            )

            assert reopened_registry.get_agent(
                "external_sql_agent_001"
            )["manifest"]["agent_id"] == MANIFEST["agent_id"]

            print("Registry survives restart: PASS")

            service = Phase19PersistentAssuranceService(
                registry=reopened_registry,
                audit=audit,
            )

            result = service.run_assurance(
                "external_sql_agent_001",
                "generate_sql",
                TESTS,
                approved_run=True,
            )

            assert result["report"]["passed_tests"] == 2
            assert result["report"]["failed_tests"] == 0
            assert result["audit_verified"] is True

            print("Mock assurance execution: PASS")
            print("Persistent audit verification: PASS")

            # Simulate revocation.
            current_review = make_review(approved=False)

            try:
                service.run_assurance(
                    "external_sql_agent_001",
                    "generate_sql",
                    TESTS,
                    approved_run=True,
                )
            except PermissionError:
                print("Revoked approval blocked: PASS")
            else:
                raise AssertionError(
                    "Revoked agent was allowed to run"
                )

            # Previously stored evidence remains available.
            evidence_id = result["evidence_id"]
            assert audit.verify_report(evidence_id)

            print("Historical evidence retained: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 19.4: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
