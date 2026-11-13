
"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Agent Assurance Engine

Responsibilities:
1. Validate agent manifests.
2. Verify agent capabilities.
3. Check execution configuration.
4. Verify security allowlists.
5. Check pre-activation status.
6. Generate assurance results.

Important:
This engine performs configuration assurance only.
It does not execute agents, approve agents,
or activate agents.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.discovery.manifest_validator import (
    validate_discovered_agent,
)


class AssuranceEngine:
    """
    Run configuration assurance checks
    against a discovered or registered agent.
    """

    def run(
        self,
        manifest: BaseModel | dict[str, Any],
    ) -> dict[str, Any]:

        # --------------------------------------
        # Normalize input
        # --------------------------------------

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

        # --------------------------------------
        # Helper to record test results
        # --------------------------------------

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

        # --------------------------------------
        # Test 1: Manifest validation
        # --------------------------------------

        validation = validate_discovered_agent(data)

        add_check(
            name="manifest_validation",
            passed=validation.valid,
            message=(
                "Manifest validation passed."
                if validation.valid
                else "; ".join(validation.errors)
            ),
        )

        # --------------------------------------
        # Test 2: Inactive status
        # --------------------------------------

        add_check(
            name="inactive_status",
            passed=data.get("status") == "inactive",
            message=(
                "Agent must remain inactive "
                "before governance approval."
            ),
        )

        # --------------------------------------
        # Test 3: Capabilities
        # --------------------------------------

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
            name="capability_declaration",
            passed=valid_capabilities,
            message=(
                "Agent must declare at least "
                "one valid capability."
            ),
        )

        # --------------------------------------
        # Test 4: Provider validation
        # --------------------------------------

        provider = data.get("provider")

        add_check(
            name="supported_provider",
            passed=provider in {
                "databricks",
                "langgraph",
                "external",
            },
            message="Agent provider must be supported.",
        )

        # --------------------------------------
        # Test 5: Execution configuration
        # --------------------------------------

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
            name="execution_configuration",
            passed=execution_valid,
            message=(
                "Agent execution configuration "
                "must be complete."
            ),
        )

        # --------------------------------------
        # Calculate assurance score
        # --------------------------------------

        total_checks = len(checks)

        passed_checks = sum(
            1 for check in checks
            if check["passed"]
        )

        score = (
            round(
                passed_checks / total_checks * 100,
                2,
            )
            if total_checks
            else 0.0
        )

        passed = (
            total_checks > 0
            and passed_checks == total_checks
        )

        # --------------------------------------
        # Return structured result
        # --------------------------------------

        return {
            "agent_id": agent_id,
            "assurance_type": "pre_activation_configuration",
            "status": (
                "passed" if passed else "failed"
            ),
            "passed": passed,
            "score": score,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
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
    Convenience function for onboarding integration.
    """

    engine = AssuranceEngine()

    return engine.run(manifest)
