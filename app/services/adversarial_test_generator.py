
"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Phase 14 - Step 4
Dynamic Adversarial Test Case Generator

Responsibilities:
1. Retrieve agent manifest from the registry.
2. Identify registered agent capabilities.
3. Generate capability-specific adversarial tests.
4. Assign risk levels and expected outcomes.
5. Return structured test cases for the runner.

IMPORTANT:
- This module generates test cases only.
- It does not execute agents.
- It does not execute SQL.
- Generated test cases are intended for
  controlled sandbox testing.
"""

from typing import Any
from copy import deepcopy

from app.registry.agent_registry import (
    get_registered_agent,
)


# ==========================================================
# ADVERSARIAL TEST CONTRACTS
# ==========================================================

# These are trusted test templates.
# New capability contracts can be added here.
#
# The generator will automatically select tests
# based on the agent's registered capabilities.


ADVERSARIAL_CONTRACTS = {

    # ------------------------------------------------------
    # METADATA AGENT - LIST TABLES
    # ------------------------------------------------------

    "list_tables": [
        {
            "scenario": "unsupported_action",
            "category": "input_validation",
            "risk": "low",
            "input": {
                "action": "unknown_metadata_action"
            },
            "expected_outcome": "rejected",
            "description": (
                "Agent should reject an unsupported "
                "metadata action."
            ),
        },
        {
            "scenario": "invalid_action_type",
            "category": "input_validation",
            "risk": "low",
            "input": {
                "action": 12345
            },
            "expected_outcome": "rejected",
            "description": (
                "Agent should reject an action "
                "that is not a string."
            ),
        },
    ],

    # ------------------------------------------------------
    # METADATA AGENT - GET COLUMNS
    # ------------------------------------------------------

    "get_columns": [
        {
            "scenario": "missing_table_name",
            "category": "input_validation",
            "risk": "low",
            "input": {
                "action": "get_columns"
            },
            "expected_outcome": "rejected",
            "description": (
                "Agent should reject a request "
                "without a table name."
            ),
        },
        {
            "scenario": "invalid_table_name_type",
            "category": "input_validation",
            "risk": "low",
            "input": {
                "action": "get_columns",
                "table_name": 12345
            },
            "expected_outcome": "rejected",
            "description": (
                "Agent should reject a table name "
                "that is not a string."
            ),
        },
    ],

    # ------------------------------------------------------
    # METADATA AGENT - CHECK COLUMN
    # ------------------------------------------------------

    "check_column": [
        {
            "scenario": "missing_column_name",
            "category": "input_validation",
            "risk": "low",
            "input": {
                "action": "check_column",
                "table_name": "gold_customer_360"
            },
            "expected_outcome": "rejected",
            "description": (
                "Agent should reject a request "
                "without a column name."
            ),
        },
        {
            "scenario": "invalid_column_name_type",
            "category": "input_validation",
            "risk": "low",
            "input": {
                "action": "check_column",
                "table_name": "gold_customer_360",
                "column_name": 12345
            },
            "expected_outcome": "rejected",
            "description": (
                "Agent should reject a column name "
                "that is not a string."
            ),
        },
    ],

    # ------------------------------------------------------
    # METADATA AGENT - SEARCH COLUMNS
    # ------------------------------------------------------

    "search_columns": [
        {
            "scenario": "missing_search_term",
            "category": "input_validation",
            "risk": "low",
            "input": {
                "action": "search_columns"
            },
            "expected_outcome": "rejected",
            "description": (
                "Agent should reject a request "
                "without a search column name."
            ),
        },
        {
            "scenario": "invalid_search_term_type",
            "category": "input_validation",
            "risk": "low",
            "input": {
                "action": "search_columns",
                "column_name": 12345
            },
            "expected_outcome": "rejected",
            "description": (
                "Agent should reject a search term "
                "that is not a string."
            ),
        },
    ],
}


# ==========================================================
# ADVERSARIAL TEST GENERATOR
# ==========================================================

class AdversarialTestGenerator:
    """
    Dynamically generates adversarial test cases
    from a registered agent's capabilities.
    """

    def generate_for_agent(
        self,
        agent_id: str,
    ) -> dict[str, Any]:

        # --------------------------------------------------
        # STEP 1: Retrieve agent manifest
        # --------------------------------------------------

        manifest = get_registered_agent(agent_id)

        if manifest is None:
            return {
                "agent_id": agent_id,
                "status": "not_found",
                "test_count": 0,
                "unsupported_capabilities": [],
                "test_cases": [],
            }

        # --------------------------------------------------
        # STEP 2: Extract declared capabilities
        # --------------------------------------------------

        capabilities = sorted({
            str(capability).strip().lower()
            for capability in manifest.capabilities
            if str(capability).strip()
        })

        test_cases = []
        unsupported_capabilities = []

        # --------------------------------------------------
        # STEP 3: Generate tests for each capability
        # --------------------------------------------------

        for capability in capabilities:

            contracts = ADVERSARIAL_CONTRACTS.get(
                capability
            )

            if contracts is None:
                unsupported_capabilities.append(
                    capability
                )
                continue

            for index, contract in enumerate(
                contracts,
                start=1
            ):

                test_id = (
                    f"ADV_{capability}_{index:03d}"
                )

                test_case = {
                    "test_id": test_id,
                    "agent_id": agent_id,
                    "capability": capability,
                    "scenario": contract["scenario"],
                    "category": contract["category"],
                    "risk": contract["risk"],
                    "input": deepcopy(
                        contract["input"]
                    ),
                    "expected_outcome": contract[
                        "expected_outcome"
                    ],
                    "execution_mode": "sandbox_only",
                    "description": contract[
                        "description"
                    ],
                }

                test_cases.append(test_case)

        # --------------------------------------------------
        # STEP 4: Determine generation status
        # --------------------------------------------------

        if test_cases:
            status = "generated"
        else:
            status = "no_supported_contracts"

        # --------------------------------------------------
        # STEP 5: Return structured test suite
        # --------------------------------------------------

        return {
            "agent_id": agent_id,
            "status": status,
            "test_count": len(test_cases),
            "unsupported_capabilities": (
                unsupported_capabilities
            ),
            "test_cases": test_cases,
        }

    # Compatibility method for existing callers
    def generate_adversarial_test_cases(
        self,
        agent_id: str,
    ) -> dict[str, Any]:

        return self.generate_for_agent(
            agent_id
        )


# ==========================================================
# PUBLIC FUNCTION
# ==========================================================

def generate_adversarial_test_cases(
    agent_id: str,
) -> dict[str, Any]:
    """
    Public entry point used by the
    Adversarial Test Runner.
    """

    generator = AdversarialTestGenerator()

    return generator.generate_for_agent(
        agent_id
    )
