"""
HEAAP Phase 16.4
Mock SQL Agent for adapter testing.

No SQL generation, database connection, or SQL execution.
"""

from typing import Any


class MockSQLAgent:

    ALLOWED_ACTIONS = {
        "generate_sql",
        "validate_sql",
    }

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:

        if not isinstance(payload, dict):
            return self.reject(
                "INVALID_INPUT",
                "Payload must be an object",
            )

        action = payload.get("action")

        if not isinstance(action, str) or not action:
            return self.reject(
                "INVALID_INPUT",
                "Action must be a non-empty string",
            )

        if action not in self.ALLOWED_ACTIONS:
            return self.reject(
                "INVALID_ACTION",
                "Unsupported SQL Agent action",
            )

        field = (
            "question"
            if action == "generate_sql"
            else "sql_query"
        )

        value = payload.get(field)

        if not isinstance(value, str) or not value.strip():
            return self.reject(
                "INVALID_INPUT",
                f"{field} must be a non-empty string",
            )

        # Only return mock responses.
        if action == "generate_sql":
            return {
                "status": "success",
                "agent_id": "sql_agent_001",
                "action": action,
                "result": {
                    "sql": "SELECT 1 AS mock_result",
                    "mock": True,
                },
            }

        return {
            "status": "success",
            "agent_id": "sql_agent_001",
            "action": action,
            "result": {
                "valid": True,
                "mock": True,
            },
        }

    @staticmethod
    def reject(code: str, message: str) -> dict[str, Any]:
        return {
            "status": "rejected",
            "error_code": code,
            "message": message,
        }
