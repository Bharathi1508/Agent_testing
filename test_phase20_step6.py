"""HEAAP Phase 20.6 - Automated contract verification tests."""

import json
import tempfile
from pathlib import Path

from app.services.capability_contract_verifier import (
    MockCapabilityTransport,
    CapabilityContractVerifier,
    validate_response,
    save_contract_report,
)


def main():
    print("HEAAP PHASE 20.6 - CAPABILITY CONTRACT TESTING")
    print("=" * 60)

    responses = {
        ("sql_agent_001", "generate_sql"): {
            "sql": "SELECT policy_id FROM policies"
        },
        ("sql_agent_001", "validate_sql"): {
            "valid": True,
            "reason": "Query structure accepted",
        },
        ("metadata_agent_001", "get_metadata"): {
            "columns": [
                {"name": "policy_id", "data_type": "string"},
                {"name": "premium", "data_type": "double"},
            ]
        },
        ("fraud_agent_001", "detect_fraud"): {
            "fraud_score": 0.87,
            "flagged": True,
        },
        ("invalid_sql_agent", "generate_sql"): {
            "sql": ""
        },
    }

    transport = MockCapabilityTransport(responses)
    verifier = CapabilityContractVerifier(transport)

    sql = verifier.verify(
        "sql_agent_001",
        ["generate_sql", "validate_sql"],
        mock_run_authorized=True,
    )

    assert sql["verdict"] == "PASS"
    assert sql["passed"] == 2
    print("SQL Agent contracts: PASS")

    metadata = verifier.verify(
        "metadata_agent_001",
        ["get_metadata"],
        mock_run_authorized=True,
    )

    assert metadata["verdict"] == "PASS"
    print("Metadata Agent contract: PASS")

    fraud = verifier.verify(
        "fraud_agent_001",
        ["detect_fraud"],
        mock_run_authorized=True,
    )

    assert fraud["verdict"] == "PASS"
    print("Fraud Agent contract: PASS")

    invalid = verifier.verify(
        "invalid_sql_agent",
        ["generate_sql"],
        mock_run_authorized=True,
    )

    assert invalid["verdict"] == "FAIL"
    print("Invalid SQL response detected: PASS")

    unsupported = verifier.verify(
        "new_agent_001",
        ["explain_fraud"],
        mock_run_authorized=True,
    )

    assert unsupported["verdict"] == "UNSUPPORTED"
    print("Unknown capability quarantined: PASS")

    invalid_score = validate_response(
        "detect_fraud",
        {"fraud_score": 1.5, "flagged": True},
    )

    assert invalid_score["status"] == "FAIL"
    print("Invalid fraud score rejected: PASS")

    invalid_type = validate_response(
        "validate_sql",
        {"valid": "true", "reason": "Accepted"},
    )

    assert invalid_type["status"] == "FAIL"
    print("Incorrect response type rejected: PASS")

    try:
        verifier.verify(
            "sql_agent_001",
            ["generate_sql"],
        )
    except PermissionError:
        print("Missing mock authorization blocked: PASS")
    else:
        raise AssertionError("Unauthorized mock run accepted")

    with tempfile.TemporaryDirectory() as directory:
        path = save_contract_report(
            sql,
            output_dir=Path(directory),
        )

        saved = json.loads(
            Path(path).read_text(encoding="utf-8-sig")
        )

        assert saved["verdict"] == "PASS"
        assert saved["governance"]["live_endpoint_invoked"] is False

        print("Assurance report saved and verified: PASS")

    assert sql["governance"]["production_approved"] is False
    assert sql["governance"][
        "capabilities_independently_verified"
    ] is False

    print("Production approval not granted: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 20.6: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
