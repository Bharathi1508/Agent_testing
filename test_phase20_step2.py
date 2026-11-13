"""HEAAP Phase 20.2 - Automatic onboarding tests."""

import json
import tempfile
from pathlib import Path

from app.services.automatic_agent_onboarding import (
    create_pending_onboarding_review,
    validate_discovery_metadata,
)


def main():
    print("HEAAP PHASE 20.2 - AUTOMATIC AGENT ONBOARDING")
    print("=" * 60)

    discoveries = [
        {
            "provider": "databricks",
            "agent_id": "new_sql_agent_001",
            "endpoint_name": "sql-agent-endpoint",
            "declared_capabilities": [
                "generate_sql",
                "validate_sql",
            ],
        },
        {
            "provider": "langgraph",
            "agent_id": "new_metadata_agent_001",
            "endpoint_name": "metadata-agent-endpoint",
            "declared_capabilities": [
                "get_metadata",
            ],
        },
        {
            "provider": "custom_rest",
            "agent_id": "new_fraud_agent_001",
            "endpoint_name": "fraud-agent-endpoint",
            "declared_capabilities": [
                "detect_fraud",
                "explain_fraud",
            ],
        },
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        results = []

        for discovery in discoveries:
            result = create_pending_onboarding_review(
                discovery,
                output_dir=Path(temp_dir),
            )
            results.append(result)

            assert Path(result["review_file"]).is_file()
            assert Path(result["manifest_file"]).is_file()
            assert Path(result["plan_file"]).is_file()

            assert (
                result["review"]["review_status"]
                == "pending_manual_review"
            )
            assert (
                result["review"]["execution_authorized"]
                is False
            )
            assert (
                result["review"]["automatically_registered"]
                is False
            )

        print("Three new agents processed: PASS")
        print("Onboarding JSON files generated: PASS")
        print("Pending review enforced: PASS")

        sql = results[0]
        assert sql["test_plan"]["total_tests"] == 4
        print("SQL Agent capability mapping: PASS")

        metadata = results[1]
        assert metadata["test_plan"]["total_tests"] == 1
        print("Metadata Agent capability mapping: PASS")

        fraud = results[2]
        assert fraud["test_plan"]["total_tests"] == 1
        assert fraud["test_plan"]["unsupported_capabilities"] == [
            "explain_fraud"
        ]
        print("Unknown Fraud capability flagged: PASS")

        for result in results:
            saved_review = json.loads(
                Path(result["review_file"]).read_text(
                    encoding="utf-8"
                )
            )
            assert saved_review["review_status"] == (
                "pending_manual_review"
            )

        print("Saved review records verified: PASS")

    invalid = {
        "provider": "databricks",
        "agent_id": "invalid_agent",
        "endpoint_name": "test-endpoint",
        "declared_capabilities": [
            "generate_sql",
            "generate_sql",
        ],
    }

    try:
        validate_discovery_metadata(invalid)
    except ValueError:
        print("Duplicate capabilities rejected: PASS")
    else:
        raise AssertionError(
            "Duplicate capabilities were accepted"
        )

    invalid_provider = {
        "provider": "unknown_provider",
        "agent_id": "invalid_agent",
        "endpoint_name": "test-endpoint",
        "declared_capabilities": ["generate_sql"],
    }

    try:
        validate_discovery_metadata(invalid_provider)
    except ValueError:
        print("Unsupported provider rejected: PASS")
    else:
        raise AssertionError(
            "Unsupported provider was accepted"
        )

    print()
    print("Live endpoints invoked: False")
    print("Agents automatically approved: False")
    print("Agents automatically registered: False")
    print("PHASE 20.2: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
