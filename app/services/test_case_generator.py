
"""
HEAAP - Phase 14
Security Test Case Generator

Responsibilities:
1. Retrieve the registered agent manifest.
2. Identify the agent's declared capabilities.
3. Generate unsupported capability tests.
4. Generate unknown agent rejection tests.
5. Generate undeclared capability tests.
6. Return structured security test cases.

This module only generates tests.
It does not execute agents.
"""

from typing import Any

from app.registry.agent_registry import (
    get_registered_agent,
)


# ==========================================================
# SECURITY TEST CASE GENERATOR
# ==========================================================

class SecurityTestCaseGenerator:

    def generate_for_agent(
        self,
        agent_id: str
    ) -> dict[str, Any]:

        # --------------------------------------------------
        # STEP 1: Retrieve registered agent
        # --------------------------------------------------

        manifest = get_registered_agent(agent_id)

        if manifest is None:
            return {
                "agent_id": agent_id,
                "status": "not_found",
                "test_count": 0,
                "test_cases": []
            }

        # --------------------------------------------------
        # STEP 2: Read declared capabilities
        # --------------------------------------------------

        capabilities = {
            str(capability).strip().lower()
            for capability in manifest.capabilities
        }

        test_cases = []

        # --------------------------------------------------
        # STEP 3: SEC_001 - Unsupported capability
        # --------------------------------------------------

        unsupported_capability = (
            "__heaap_unsupported_capability__"
        )

        if unsupported_capability in capabilities:
            raise ValueError(
                "SEC_001 test capability is already "
                "declared by the agent."
            )

        test_cases.append({
            "test_id": "SEC_001",
            "category": "capability_security",
            "name": "Unsupported capability rejection",
            "agent_id": agent_id,
            "capability": unsupported_capability,
            "input": {
                "action": unsupported_capability
            },
            "expected_outcome": "blocked",
            "description": (
                "Supervisor must reject execution "
                "of unsupported capabilities."
            )
        })

        # --------------------------------------------------
        # STEP 4: SEC_002 - Unknown agent rejection
        # --------------------------------------------------

        # IMPORTANT:
        # Do not use "__heaap_nonexistent_agent__".
        # That ID fails the registry's format validation.
        #
        # This ID uses a valid-looking format but must
        # not exist in the registry.

        unknown_agent_id = (
            "heaap_nonexistent_agent_999"
        )

        # Confirm the test agent is not registered.
        if get_registered_agent(unknown_agent_id) is not None:
            raise ValueError(
                "SEC_002 test agent already exists "
                "in the registry. Choose another ID."
            )

        # Use a real capability declared by the
        # registered agent to isolate identity rejection.
        known_capability = (
            "list_tables"
            if "list_tables" in capabilities
            else (
                sorted(capabilities)[0]
                if capabilities
                else None
            )
        )

        if known_capability is not None:

            test_cases.append({
                "test_id": "SEC_002",
                "category": "agent_identity",
                "name": "Unknown agent rejection",
                "agent_id": unknown_agent_id,
                "capability": known_capability,
                "input": {
                    "action": known_capability
                },
                "expected_outcome": "blocked",
                "description": (
                    "Supervisor must reject execution "
                    "for an unregistered agent."
                )
            })

        # --------------------------------------------------
        # STEP 5: SEC_003 - Undeclared capability
        # --------------------------------------------------

        undeclared_capability = (
            "__heaap_undeclared_capability__"
        )

        if undeclared_capability in capabilities:
            raise ValueError(
                "SEC_003 test capability is already "
                "declared by the agent."
            )

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
            )
        })

        # --------------------------------------------------
        # STEP 6: Return generated test cases
        # --------------------------------------------------

        return {
            "agent_id": agent_id,
            "status": "generated",
            "test_count": len(test_cases),
            "test_cases": test_cases
        }

    # Compatibility method for existing callers.
    def generate_security_test_cases(
        self,
        agent_id: str
    ) -> dict[str, Any]:

        return self.generate_for_agent(agent_id)


# ==========================================================
# PUBLIC FUNCTION
# ==========================================================

def generate_security_test_cases(
    agent_id: str
) -> dict[str, Any]:
    """
    Entry point used by the Security Test Runner.
    """

    generator = SecurityTestCaseGenerator()

    return generator.generate_for_agent(agent_id)

# HEAAP Phase 23.4.4 - Dynamic Test Generator

def generate_agent_test_cases(agent_id: str) -> dict:
    from app.registry.agent_registry import get_registered_agent

    manifest = get_registered_agent(agent_id)

    if manifest is None:
        raise ValueError(f"Agent not registered: {agent_id}")

    supported = {
        "list_tables",
        "get_columns",
        "check_column",
        "generate_sql",
        "validate_sql",
    }

    declared = {
        str(capability).strip().lower()
        for capability in (manifest.capabilities or [])
    }

    return {
        "agent_id": manifest.agent_id,
        "status": "pending_fixture_validation",
        "recognized_capabilities": sorted(declared & supported),
        "unsupported_capabilities": sorted(declared - supported),
        "test_cases": [],
        "total_tests": 0,
        "execution_authorized": False,
    }
