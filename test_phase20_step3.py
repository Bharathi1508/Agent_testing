"""HEAAP Phase 20.3 - Automated discovery tests."""

import json
import tempfile
from pathlib import Path

from app.services.offline_endpoint_discovery_provider import (
    OfflineEndpointDiscoveryProvider,
)
from app.services.automated_endpoint_discovery_pipeline import (
    AutomatedEndpointDiscoveryPipeline,
)


def main():
    print("HEAAP PHASE 20.3 - AUTOMATED ENDPOINT DISCOVERY")
    print("=" * 60)

    fixture = Path(
        "reports/phase20_3/discovery_fixture.json"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        working_fixture = root / "discovery.json"

        working_fixture.write_text(
            fixture.read_text(encoding="utf-8-sig"),
            encoding="utf-8",
        )

        provider = OfflineEndpointDiscoveryProvider(
            working_fixture
        )

        pipeline = AutomatedEndpointDiscoveryPipeline(
            provider,
            output_dir=root / "results",
        )

        first = pipeline.run_discovery()

        assert first["total_discovered"] == 3
        assert first["new"] == 3
        assert first["errors"] == 0

        print("Three new agents discovered: PASS")

        second = pipeline.run_discovery()

        assert second["unchanged"] == 3
        assert second["new"] == 0

        print("Previously seen agents skipped: PASS")

        payload = json.loads(
            working_fixture.read_text(
                encoding="utf-8"
            )
        )

        payload["endpoints"][0][
            "declared_capabilities"
        ] = ["generate_sql"]

        working_fixture.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        third = pipeline.run_discovery()

        assert third["changed"] == 1
        assert third["unchanged"] == 2

        print("Changed agent metadata detected: PASS")

        changed = [
            r for r in third["results"]
            if r["status"] == "changed"
        ]

        assert len(changed) == 1

        changed_review = json.loads(
            Path(changed[0]["review_file"]).read_text(
                encoding="utf-8"
            )
        )

        assert changed_review["review_status"] == (
            "pending_manual_review"
        )
        assert changed_review["execution_authorized"] is False

        print("Changed agent requires new review: PASS")

        assert third["governance"][
            "automatically_approved"
        ] is False

        assert third["governance"][
            "automatically_registered"
        ] is False

        print("Automatic approval prevented: PASS")

        assert Path(third["report_file"]).is_file()

        print("Discovery report persisted: PASS")

        # Malformed discovery metadata must be rejected.
        payload["endpoints"].append({
            "provider": "unknown",
            "agent_id": "bad_agent",
            "endpoint_name": "bad-endpoint",
            "declared_capabilities": ["generate_sql"],
        })

        working_fixture.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        fourth = pipeline.run_discovery()

        assert fourth["errors"] == 1

        print("Invalid discovery metadata rejected: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 20.3: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
