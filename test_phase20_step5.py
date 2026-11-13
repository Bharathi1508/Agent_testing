"""HEAAP Phase 20.5 - Capability identification tests."""

import tempfile
from pathlib import Path

from app.services.endpoint_capability_identification import (
    EndpointCapabilityIdentificationService,
)


def main():
    print("HEAAP PHASE 20.5 - CAPABILITY IDENTIFICATION")
    print("=" * 60)

    endpoints = [
        {"name": "sql-agent-endpoint"},
        {"name": "metadata-agent-endpoint"},
        {"name": "fraud-agent-endpoint"},
        {"name": "unknown-agent-endpoint"},
    ]

    catalog_file = (
        "reports/phase20_5/capability_catalog.json"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        service = EndpointCapabilityIdentificationService(
            catalog_file=catalog_file,
            output_dir=Path(temp_dir),
        )

        report = service.identify(endpoints)

        assert report["total_endpoints"] == 4
        print("Four endpoints inspected: PASS")

        assert report["pending_review"] == 3
        print("Three declared agents identified: PASS")

        assert report["quarantined"] == 1
        print("Unknown endpoint quarantined: PASS")

        results = {
            item["endpoint_name"]: item
            for item in report["results"]
        }

        sql = results["sql-agent-endpoint"]

        assert sql["declared_capabilities"] == [
            "generate_sql",
            "validate_sql",
        ]
        assert sql["planned_tests"] == 4

        print("SQL capability mapping: PASS")

        metadata = results["metadata-agent-endpoint"]

        assert metadata["planned_tests"] == 1
        print("Metadata capability mapping: PASS")

        fraud = results["fraud-agent-endpoint"]

        assert fraud["planned_tests"] == 1
        print("Fraud capability mapping: PASS")

        unknown = results["unknown-agent-endpoint"]

        assert unknown["status"] == "quarantined"
        print("Unknown capability safely handled: PASS")

        for item in report["results"]:
            assert item["execution_authorized"] is False
            assert item["automatically_registered"] is False

        print("Automatic execution and registration blocked: PASS")

        for name in [
            "sql-agent-endpoint",
            "metadata-agent-endpoint",
            "fraud-agent-endpoint",
        ]:
            assert Path(results[name]["review_file"]).is_file()
            assert Path(results[name]["manifest_file"]).is_file()
            assert Path(results[name]["plan_file"]).is_file()

        print("Onboarding artifacts generated: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 20.5: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
