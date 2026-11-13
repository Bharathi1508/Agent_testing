from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.registry.agent_registry import list_registered_agents


# Registry of available assurance suites.
# Add new suites here when new evaluators are implemented.
SUITE_CATALOG = {
    "metadata_assurance": {
        "capabilities": {
            "list_tables",
            "get_columns",
            "check_column",
        },
        "test_types": [
            "table_discovery",
            "column_existence",
            "data_type_validation",
        ],
    },
    "sql_assurance": {
        "capabilities": {
            "generate_sql",
            "validate_sql",
        },
        "test_types": [
            "sql_generation",
            "sql_syntax_validation",
            "sql_safety_validation",
            "schema_reference_validation",
        ],
    },
}


def assign_test_suites(agent):
    declared = set(agent.capabilities or [])
    assignments = []
    covered = set()

    for suite_name, suite in SUITE_CATALOG.items():
        matched = sorted(
            declared.intersection(suite["capabilities"])
        )

        if not matched:
            continue

        covered.update(matched)

        assignments.append({
            "suite": suite_name,
            "matched_capabilities": matched,
            "planned_test_types": suite["test_types"],
            "assignment_status": "assigned_not_executed",
        })

    return {
        "agent_id": agent.agent_id,
        "agent_name": agent.name,
        "status": agent.status,
        "execution_type": agent.execution_type,
        "framework": agent.framework,
        "declared_capabilities": sorted(declared),
        "assigned_suites": assignments,
        "unsupported_capabilities": sorted(
            declared - covered
        ),
        "execution_authorized": False,
        "governance_check_required": True,
    }


def build_assignment_plan():
    agents = list_registered_agents()

    plans = [
        assign_test_suites(agent)
        for agent in agents
    ]

    return {
        "phase": "23.4.3",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_agents": len(plans),
        "total_suite_assignments": sum(
            len(p["assigned_suites"]) for p in plans
        ),
        "agents": plans,
    }


def main():
    plan = build_assignment_plan()

    output_dir = Path("reports/phase23_4")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d_%H%M%S_%f")

    output = output_dir / (
        f"test_assignment_{timestamp}.json"
    )

    with output.open("x", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)

    print("=== PHASE 23.4.3 ===")
    print("Agents discovered:", plan["total_agents"])
    print(
        "Suite assignments:",
        plan["total_suite_assignments"],
    )

    for agent in plan["agents"]:
        print("\nAgent:", agent["agent_id"])
        print("Status:", agent["status"])

        for suite in agent["assigned_suites"]:
            print("Assigned:", suite["suite"])
            print(
                "Capabilities:",
                suite["matched_capabilities"],
            )

        if agent["unsupported_capabilities"]:
            print(
                "Unsupported:",
                agent["unsupported_capabilities"],
            )

    print("\nReport:", output)


if __name__ == "__main__":
    main()
