"""HEAAP Phase 20.0 - Dynamic multi-agent assurance tests."""

import tempfile
from pathlib import Path

from app.services.dynamic_multi_agent_assurance import (
    DynamicMultiAgentAssuranceCoordinator,
    save_multi_agent_report,
)


def make_agent(agent_id, capabilities, approved):
    manifest = {
        "agent_id": agent_id,
        "endpoint_name": "mock-" + agent_id,
        "capabilities": capabilities,
    }

    review = {
        "review_id": "synthetic-review-" + agent_id,
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

    return {
        "manifest": manifest,
        "review": review,
    }


def main():
    print("HEAAP PHASE 20.0 - DYNAMIC MULTI-AGENT ASSURANCE")
    print("=" * 60)

    agents = [
        make_agent(
            "sql_agent_001",
            ["generate_sql", "validate_sql"],
            True,
        ),
        make_agent(
            "metadata_agent_001",
            ["get_metadata"],
            False,
        ),
        make_agent(
            "fraud_agent_001",
            ["detect_fraud"],
            True,
        ),
        make_agent(
            "new_agent_001",
            ["unknown_capability"],
            True,
        ),
    ]

    coordinator = DynamicMultiAgentAssuranceCoordinator()

    report = coordinator.evaluate_agents(agents)

    assert report["total_agents"] == 4
    print("Four agents evaluated: PASS")

    results = {
        item["agent_id"]: item
        for item in report["agents"]
    }

    sql = results["sql_agent_001"]
    assert sql["total_planned_tests"] == 4
    assert sql["verdict"] == "READY_FOR_RUN_APPROVAL"
    print("SQL Agent test planning: PASS")

    metadata = results["metadata_agent_001"]
    assert metadata["total_planned_tests"] == 1
    assert metadata["verdict"] == "BLOCKED"
    print("Pending Metadata Agent blocked: PASS")

    fraud = results["fraud_agent_001"]
    assert fraud["total_planned_tests"] == 1
    assert fraud["verdict"] == "READY_FOR_RUN_APPROVAL"
    print("Fraud Agent test planning: PASS")

    unknown = results["new_agent_001"]
    assert unknown["total_planned_tests"] == 0
    assert unknown["unsupported_capabilities"] == [
        "unknown_capability"
    ]
    assert unknown["verdict"] == "BLOCKED"
    print("Unknown capability blocked: PASS")

    assert report["ready_for_run_approval"] == 2
    assert report["blocked_agents"] == 2
    print("Consolidated verdict counts: PASS")

    assert all(
        item["tests_executed"] == 0
        for item in report["agents"]
    )
    assert report["governance"]["execution_authorized"] is False
    assert report["governance"]["live_endpoint_invoked"] is False
    print("No external execution: PASS")

    with tempfile.TemporaryDirectory() as temp_dir:
        report_file = save_multi_agent_report(
            report,
            output_dir=Path(temp_dir),
        )

        assert Path(report_file).is_file()
        print("Consolidated JSON report saved: PASS")

    try:
        coordinator.evaluate_agents([
            agents[0],
            agents[0],
        ])
    except ValueError:
        print("Duplicate agent registration rejected: PASS")
    else:
        raise AssertionError(
            "Duplicate agent ID was accepted"
        )

    print()
    print("Agents evaluated:", report["total_agents"])
    print(
        "Ready for run approval:",
        report["ready_for_run_approval"],
    )
    print("Blocked:", report["blocked_agents"])
    print("Live endpoint invoked: False")
    print("Production approved: False")
    print("PHASE 20.0: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
