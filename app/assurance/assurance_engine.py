
"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Phase 11: Agent Assurance Engine

Performs pre-activation configuration checks
on dynamically onboarded agents.

This engine does not:
- Execute agent endpoints
- Approve agents
- Activate agents
- Modify the registry
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.discovery.manifest_validator import (
    validate_discovered_agent,
)


class AssuranceEngine:
    """
    Validates agent configuration before
    functional testing and governance approval.
    """

    def run(
        self,
        manifest: BaseModel | dict[str, Any],
    ) -> dict[str, Any]:

        if isinstance(manifest, BaseModel):
            data = manifest.model_dump(mode="json")
        elif isinstance(manifest, dict):
            data = manifest.copy()
        else:
            raise TypeError(
                "Manifest must be a dictionary "
                "or Pydantic model."
            )

        agent_id = str(data.get("agent_id", ""))

        checks: list[dict[str, Any]] = []

        def add_check(
            name: str,
            passed: bool,
            message: str,
        ) -> None:
            checks.append({
                "name": name,
                "passed": bool(passed),
                "message": message,
            })

        # 1. Validate manifest and allowlists
        discovery_data = data.copy()
        discovery_data.pop("status", None)

        validation = validate_discovered_agent(discovery_data)

        add_check(
            "manifest_validation",
            validation.valid,
            (
                "Manifest validation passed."
                if validation.valid
                else "; ".join(validation.errors)
            ),
        )

        # 2. Require inactive status
        add_check(
            "inactive_status",
            data.get("status") == "inactive",
            "Agent must be inactive before approval.",
        )

        # 3. Validate capability declarations
        capabilities = data.get("capabilities")

        valid_capabilities = (
            isinstance(capabilities, list)
            and len(capabilities) > 0
            and all(
                isinstance(capability, str)
                and bool(capability.strip())
                for capability in capabilities
            )
        )

        add_check(
            "capability_declaration",
            valid_capabilities,
            "Agent must declare valid capabilities.",
        )

        # 4. Validate supported provider
        provider = data.get("provider")

        add_check(
            "supported_provider",
            provider in {
                "databricks",
                "langgraph",
                "external",
            },
            "Agent provider must be supported.",
        )

        # 5. Validate execution configuration
        execution_type = data.get("execution_type")

        execution_valid = (
            execution_type == "local"
            or (
                execution_type == "databricks"
                and bool(data.get("endpoint_name"))
            )
            or (
                execution_type == "rest"
                and bool(data.get("endpoint_url"))
            )
        )

        add_check(
            "execution_configuration",
            execution_valid,
            "Execution configuration must be complete.",
        )

        passed_count = sum(
            check["passed"] for check in checks
        )

        total_count = len(checks)

        score = round(
            100 * passed_count / total_count,
            2,
        ) if total_count else 0.0

        passed = passed_count == total_count

        return {
            "agent_id": agent_id,
            "assurance_type": "pre_activation_configuration",
            "status": "passed" if passed else "failed",
            "passed": passed,
            "score": score,
            "total_checks": total_count,
            "passed_checks": passed_count,
            "checks": checks,
            "tested_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "requires_governance_approval": True,
        }


def run_assurance(
    manifest: BaseModel | dict[str, Any],
) -> dict[str, Any]:
    """
    Convenience function for the onboarding service.
    """
    return AssuranceEngine().run(manifest)

