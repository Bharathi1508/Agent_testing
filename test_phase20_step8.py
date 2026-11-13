"""HEAAP Phase 20.8 - Persistent multi-agent audit tests."""

import sqlite3
import tempfile
from pathlib import Path

from app.services.capability_contract_verifier import (
    MockCapabilityTransport,
)

from app.services.multi_agent_contract_supervisor import (
    MultiAgentContractSupervisor,
)

from app.services.multi_agent_persistent_audit import (
    MultiAgentPersistentAuditService,
)

from app.services.persistent_external_assurance_audit import (
    PersistentExternalAssuranceAudit,
)


def main():

    print("HEAAP PHASE 20.8 - PERSISTENT MULTI-AGENT AUDIT")
    print("=" * 60)

    responses = {
        ("sql_agent_001", "generate_sql"): {
            "sql": "SELECT policy_id FROM policies",
        },
        ("sql_agent_001", "validate_sql"): {
            "valid": True,
            "reason": "Mock validation accepted",
        },
        ("metadata_agent_001", "get_metadata"): {
            "columns": [
                {
                    "name": "policy_id",
                    "data_type": "string",
                }
            ],
        },
        ("fraud_agent_001", "detect_fraud"): {
            "fraud_score": 0.85,
            "flagged": True,
        },
    }

    manifests = [
        {
            "agent_id": "sql_agent_001",
            "capabilities": [
                "generate_sql",
                "validate_sql",
            ],
        },
        {
            "agent_id": "metadata_agent_001",
            "capabilities": ["get_metadata"],
        },
        {
            "agent_id": "fraud_agent_001",
            "capabilities": ["detect_fraud"],
        },
    ]

    with tempfile.TemporaryDirectory() as temp_dir:

        db_path = Path(temp_dir) / "heaap_audit.db"

        audit = PersistentExternalAssuranceAudit(
            db_path=db_path
        )

        supervisor = MultiAgentContractSupervisor(
            MockCapabilityTransport(responses)
        )

        service = MultiAgentPersistentAuditService(
            supervisor=supervisor,
            audit=audit,
        )

        # Test 1: Run mock assurance for three agents.
        result = service.run_and_audit(
            manifests,
            mock_run_authorized=True,
        )

        report = result["report"]

        assert report["total_agents"] == 3
        assert report["passed_agents"] == 3
        assert report["overall_verdict"] == "PASS"

        print("Three-agent mock assurance: PASS")

        # Test 2: Verify individual audit evidence.
        evidence = result["agent_evidence"]

        assert len(evidence) == 3

        for item in evidence:
            assert item["verified"] is True

            assert service.verify_evidence(
                item["evidence_id"]
            ) is True

        print("Individual agent evidence verified: PASS")

        # Test 3: Verify consolidated evidence.
        consolidated_id = result[
            "consolidated_evidence_id"
        ]

        assert service.verify_evidence(
            consolidated_id
        ) is True

        print("Consolidated evidence verified: PASS")

        # Test 4: Retrieve historical evidence.
        historical_report = service.get_evidence(
            consolidated_id
        )

        assert historical_report["total_agents"] == 3
        assert historical_report["overall_verdict"] == "PASS"

        print("Historical assurance report retrieved: PASS")

        # Test 5: Verify persistence after reopening SQLite.
        reopened_audit = PersistentExternalAssuranceAudit(
            db_path=db_path
        )

        assert reopened_audit.verify_report(
            consolidated_id
        ) is True

        print("SQLite audit survives restart: PASS")

        # Test 6: Check agent-specific history.
        sql_history = service.list_agent_history(
            "sql_agent_001"
        )

        assert len(sql_history) >= 1

        print("Agent-specific audit history: PASS")

        # Test 7: Block unauthorized mock execution.
        try:
            service.run_and_audit(
                manifests,
                mock_run_authorized=False,
            )
        except PermissionError:
            print("Unauthorized mock execution blocked: PASS")
        else:
            raise AssertionError(
                "Unauthorized mock execution was accepted"
            )

        # Test 8: Detect report tampering.
        tampered_id = evidence[0]["evidence_id"]

        with sqlite3.connect(db_path) as connection:
            connection.execute(
                """
                UPDATE assurance_evidence
                SET report_json = ?
                WHERE evidence_id = ?
                """,
                (
                    '{"agent_id":"tampered_agent"}',
                    tampered_id,
                ),
            )
            connection.commit()

        assert service.verify_evidence(
            tampered_id
        ) is False

        print("Tampered audit evidence detected: PASS")

        # Historical consolidated evidence remains intact.
        assert service.verify_evidence(
            consolidated_id
        ) is True

        print("Untampered historical evidence retained: PASS")

        assert result["live_endpoint_invoked"] is False
        assert result["production_approved"] is False

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 20.8: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
