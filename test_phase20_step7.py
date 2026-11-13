"""HEAAP Phase 20.7 - Multi-agent supervisor tests."""

import json
import tempfile
from pathlib import Path

from app.services.capability_contract_verifier import (
    MockCapabilityTransport,
)
from app.services.multi_agent_contract_supervisor import (
    MultiAgentContractSupervisor,
    save_multi_agent_contract_report,
)


def main():
    print("HEAAP PHASE 20.7 - MULTI-AGENT CONTRACT ASSURANCE")
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
            "fraud_score": 0.82,
            "flagged": True,
        },
        ("invalid_agent_001", "detect_fraud"): {
            "fraud_score": 2.5,
            "flagged": True,
        },
    }

    transport = MockCapabilityTransport(responses)
    supervisor = MultiAgentContractSupervisor(transport)

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

    report = supervisor.run(
        manifests,
        mock_run_authorized=True,
    )

    assert report["total_agents"] == 3
    assert report["passed_agents"] == 3
    assert report["overall_verdict"] == "PASS"

    print("Three agents evaluated: PASS")
    print("SQL Agent assurance: PASS")
    print("Metadata Agent assurance: PASS")
    print("Fraud Agent assurance: PASS")

    failed_report = supervisor.run(
        [
            {
                "agent_id": "sql_agent_001",
                "capabilities": ["generate_sql"],
            },
            {
                "agent_id": "invalid_agent_001",
                "capabilities": ["detect_fraud"],
            },
        ],
        mock_run_authorized=True,
    )

    assert failed_report["overall_verdict"] == "FAIL"
    assert failed_report["passed_agents"] == 1
    assert failed_report["failed_agents"] == 1

    print("Failed agent contract detected: PASS")

    unknown_report = supervisor.run(
        [
            {
                "agent_id": "unknown_agent_001",
                "capabilities": ["unknown_capability"],
            }
        ],
        mock_run_authorized=True,
    )

    assert unknown_report["overall_verdict"] == "UNSUPPORTED"
    assert unknown_report["unsupported_agents"] == 1

    print("Unsupported capability blocked: PASS")

    try:
        supervisor.run(manifests)
    except PermissionError:
        print("Unauthorized mock run blocked: PASS")
    else:
        raise AssertionError("Authorization check failed")

    try:
        supervisor.run(
            [manifests[0], manifests[0]],
            mock_run_authorized=True,
        )
    except ValueError:
        print("Duplicate agent rejected: PASS")
    else:
        raise AssertionError("Duplicate agent accepted")

    with tempfile.TemporaryDirectory() as directory:
        report_path = save_multi_agent_contract_report(
            report,
            output_dir=Path(directory),
        )

        saved = json.loads(
            Path(report_path).read_text(
                encoding="utf-8-sig"
            )
        )

        assert saved["total_agents"] == 3
        assert saved["overall_verdict"] == "PASS"

        print("Consolidated report saved: PASS")

    assert report["governance"]["live_endpoint_invoked"] is False
    assert report["governance"]["production_approved"] is False
    assert report["governance"][
        "independent_approval_verified"
    ] is False

    print("Production authorization not granted: PASS")

    print()
    print("Total agents:", report["total_agents"])
    print("Passed agents:", report["passed_agents"])
    print("Failed agents:", report["failed_agents"])
    print("Overall verdict:", report["overall_verdict"])
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 20.7: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
