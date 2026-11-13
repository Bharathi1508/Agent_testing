
"""
HEAAP - Phase 13
Functional Agent Testing Engine

Runs controlled test cases against agents
through a trusted execution adapter.
"""

import inspect
import time

from datetime import datetime, timezone
from typing import Any, Callable


class FunctionalTestingEngine:

    def __init__(
        self,
        agent_executor: Callable,
    ):
        self.agent_executor = agent_executor

    async def run_test(
        self,
        agent_id: str,
        capability: str,
        test_input: dict[str, Any],
        expected_keys: list[str],
    ) -> dict[str, Any]:

        started = time.perf_counter()

        try:
            # Execute through a trusted adapter
            result = self.agent_executor(
                agent_id=agent_id,
                capability=capability,
                payload=test_input,
            )

            if inspect.isawaitable(result):
                result = await result

            # Validate response structure
            if not isinstance(result, dict):
                raise ValueError(
                    "Agent response must be a dictionary."
                )

            missing_keys = [
                key
                for key in expected_keys
                if key not in result
            ]

            passed = len(missing_keys) == 0

            return {
                "agent_id": agent_id,
                "capability": capability,
                "status": (
                    "passed" if passed else "failed"
                ),
                "passed": passed,
                "missing_keys": missing_keys,
                "response": result,
                "execution_time_ms": round(
                    (time.perf_counter() - started) * 1000,
                    2,
                ),
                "tested_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

        except Exception as exc:

            return {
                "agent_id": agent_id,
                "capability": capability,
                "status": "error",
                "passed": False,
                "error": str(exc),
                "execution_time_ms": round(
                    (time.perf_counter() - started) * 1000,
                    2,
                ),
                "tested_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
