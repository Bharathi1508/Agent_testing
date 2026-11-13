
"""
HEAAP - Phase 14, Step 1

Security Test Case Generator

Generates safe negative tests for the
Dynamic Supervisor authorization layer.

No agent execution happens in this module.
"""

from typing import Any

from app.registry.agent_registry import (
    get_registered_agent,
)


class SecurityTestCaseGenerator:

    def generate_for_agent(
        self,
        agent_id: str,
    ) -> dict[str, Any]:

        manifest = get_registered_agent(agent_id)

        if manifest is None:
            return {
                "agent_id": agent_id,
                "status": "not_found",
                "test_count": 0,
                "test_cases": [],
            }

        declared_capabilities = {
            str(capability).strip().lower()
            for capability in manifest.capabilities
        }

        test_cases = []

        # ---------------------------------------------
        # SEC_001 - Unsupported capability
        # ---------------------------------------------

        test_cases.append({
            "test_id": "SEC_001",
            "category": "authorization",
            "name": "Unsupported capability rejection",
            "agent_id": agent_id,
            "capability": "__heaap_unsupported_capability__",
            "input": {
                "action": "__heaap_unsupported_capability__"
            },
            "expected_outcome": "blocked",
            "description": (
                "Supervisor must reject a capability "
                "not supported by the agent."
            ),
        })

        # ---------------------------------------------
        # SEC_002 - Unknown agent
        # ---------------------------------------------

        test_cases.append({
            "test_id": "SEC_002",
            "category": "agent_identity",
            "name": "Unknown agent rejection",
            "agent_id": "heaap_nonexistent_agent_999",
            "capability": "list_tables",
            "input": {
                "action": "list_tables"
            },
            "expected_outcome": "blocked",
            "description": (
                "Supervisor must reject execution "
                "for an unregistered agent."
            ),
        })

        # ---------------------------------------------
        # SEC_003 - Undeclared capability
        # ---------------------------------------------

        undeclared_capability = (
            "__heaap_undeclared_capability__"
        )

        if undeclared_capability not in declared_capabilities:

            test_cases.append({
                "test_id": "SEC_003",
                "category": "capability_governance",
                "name": "Undeclared capability rejection",
                "agent_id": agent_id,
                "capability": undeclared_capability,
                "input": {
                    "action": undeclared_capability
                },
                "expected_outcome": "blocked",
                "description": (
                    "Supervisor must prevent execution "
                    "of undeclared capabilities."
                ),
            })

        return {
            "agent_id": agent_id,
            "status": "generated",
            "test_count": len(test_cases),
            "test_cases": test_cases,
        }


def generate_security_test_cases(
    agent_id: str,
) -> dict[str, Any]:

    generator = SecurityTestCaseGenerator()

    return generator.generate_for_agent(agent_id)

