"""HEAAP Phase 20.1 - Registry discovery tests."""

import copy
import tempfile
from pathlib import Path

from app.services.registry_multi_agent_assurance import (
    RegistryMultiAgentAssuranceService,
    save_registry_assurance_report,
)


def make_agent(agent_id, capabilities, approved):
    manifest = {
        "agent_id": agent_id,
        "endpoint_name": "mock-" + agent_id,
        "capabilities": capabilities,
    }

    review = {
        "review_id": "synthetic-" + agent_id,
        "review_status": (
            "approved" if approved
            else "pending_manual_review"
        ),
        "execution_authorized": approved,
        "agent": {
            "agent_id": agent_id,
            "endpoint_name": manifest["endpoint_name"],
            "declared_capabilities": capabilities,
            "manifest_valid": True,
            "capabilities_verified": approved,
            "trust_status": (
                "verified" if approved else "unverified"
            ),
            "production_approved": False,
        },
    }

    return manifest, review


class SyntheticRegistry:
    def __init__(self, records):
        self.records = records

    def list_agents(self):
        return list(self.records.keys())

    def get_agent(self, agent_id):
        return copy.deepcopy(self.records.get(agent_id))


def main():
    print("HEAAP PHASE 20.1 - REGISTRY MULTI-AGENT ASSURANCE")
    print("=" * 60)

    definitions = [
        ("sql_agent_001", ["generate_sql", "validate_sql"], True),
        ("metadata_agent_001", ["get_metadata"], False),
        ("fraud_agent_001", ["detect_fraud"], True),
        ("new_agent_001", ["unknown_capability"], True),
    ]

    records = {}
    reviews = {}

    for agent_id, capabilities, approved in definitions:
        manifest, review = make_agent(
            agent_id,
            capabilities,
            approved,
        )

        review_file = f"synthetic/{agent_id}.json"

        records[agent_id] = {
            "manifest": manifest,
            "review_file": review_file,
        }

        reviews[review_file] = review

    # Simulate a registry entry with an unavailable review.
    records["invalid_agent_001"] = {
        "manifest": {
            "agent_id": "invalid_agent_001",
            "endpoint_name": "mock-invalid",
            "capabilities": ["get_metadata"],
        },
        "review_file": "synthetic/missing.json",
    }

    def synthetic_review_loader(review_file):
        if review_file not in reviews:
            raise FileNotFoundError(
                "Synthetic review not found"
            )
        return copy.deepcopy(reviews[review_file])

    registry = SyntheticRegistry(records)

    service = RegistryMultiAgentAssuranceService(
        registry=registry,
        review_loader=synthetic_review_loader,
    )

    report = service.evaluate_registered_agents()

    assert report["discovered_registered_agents"] == 5
    print("Five registered agents discovered: PASS")

    results = {
        item["agent_id"]: item
        for item in report["agents"]
    }

    assert (
        results["sql_agent_001"]["verdict"]
        == "READY_FOR_RUN_APPROVAL"
    )
    print("SQL Agent evaluated: PASS")

    assert results["metadata_agent_001"]["verdict"] == "BLOCKED"
    print("Pending Metadata Agent blocked: PASS")

    assert (
        results["fraud_agent_001"]["verdict"]
        == "READY_FOR_RUN_APPROVAL"
    )
    print("Fraud Agent evaluated: PASS")

    assert results["new_agent_001"]["verdict"] == "BLOCKED"
    print("Unsupported capability blocked: PASS")

    assert results["invalid_agent_001"]["verdict"] == "BLOCKED"
    print("Missing review blocked: PASS")

    assert report["ready_for_run_approval"] == 2
    assert report["blocked_agents"] == 3
    print("Consolidated counts verified: PASS")

    assert all(
        item["tests_executed"] == 0
        for item in report["agents"]
    )
    print("No agent execution performed: PASS")

    # Simulate revocation after initial assessment.
    reviews["synthetic/sql_agent_001.json"][
        "review_status"
    ] = "pending_manual_review"

    reviews["synthetic/sql_agent_001.json"][
        "execution_authorized"
    ] = False

    revoked_report = service.evaluate_registered_agents()

    revoked = {
        item["agent_id"]: item
        for item in revoked_report["agents"]
    }

    assert revoked["sql_agent_001"]["verdict"] == "BLOCKED"
    print("Changed review rechecked and blocked: PASS")

    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = save_registry_assurance_report(
            revoked_report,
            Path(temp_dir),
        )

        assert Path(output_file).is_file()
        print("Consolidated JSON report saved: PASS")

    print()
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 20.1: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
