"""
HEAAP Phase 22.15
End-to-End Metadata Assurance Runner.

Runs authorized tests against a supplied agent adapter.

Security:
- Explicit execution approval required.
- Governance authorization callback required.
- No automatic endpoint discovery.
- No simulated results presented as real assurance.
"""

from datetime import datetime, timezone

from app.services.dynamic_test_execution_engine import (
    DynamicTestExecutionEngine,
)
from app.services.agent_result_evaluator import (
    AgentResultEvaluator,
)


class MetadataAssuranceRunner:

    def __init__(
        self,
        authorization_check,
        execution_engine=None,
        evaluator=None,
    ):
        if not callable(authorization_check):
            raise ValueError(
                "A governance authorization callback is required"
            )

        self.authorization_check = authorization_check

        self.execution_engine = (
            execution_engine
            if execution_engine is not None
            else DynamicTestExecutionEngine()
        )

        self.evaluator = (
            evaluator
            if evaluator is not None
            else AgentResultEvaluator()
        )

    def run(
        self,
        agent_id,
        tests,
        adapter,
        *,
        approved_run=False,
        reference_verified=False,
    ):
        if approved_run is not True:
            raise PermissionError(
                "Explicit execution approval is required"
            )

        if reference_verified is not True:
            raise PermissionError(
                "Trusted reference verification is required"
            )

        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("Invalid agent ID")

        if not isinstance(tests, list) or not tests:
            raise ValueError("At least one test is required")

        # Must be backed by the existing persistent
        # registry and approval gate in real deployments.
        if self.authorization_check(agent_id) is not True:
            raise PermissionError(
                "Agent is not approved for execution"
            )

        execution_report = (
            self.execution_engine.execute_tests(
                agent_id,
                tests,
                adapter,
                approved_run=True,
            )
        )

        evaluation_report = (
            self.evaluator.evaluate(
                execution_report
            )
        )

        return {
            "agent_id": agent_id,
            "execution_mode": "real_agent_adapter",
            "reference_verified": True,
            "completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "execution_report": execution_report,
            "evaluation_report": evaluation_report,
        }
