from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ExternalAgentRequest:
    agent_id: str
    capability: str
    payload: Dict[str, Any]


@dataclass
class ExternalAgentResponse:
    agent_id: str
    capability: str
    status: str
    response: Dict[str, Any]
    execution_target: str
    endpoint_invoked: bool


class MockDatabricksTransport:

    def invoke(self, endpoint_name, capability, payload):

        if capability == "generate_sql":

            if payload.get("question") == "total annual premium":
                return {
                    "status": "success",
                    "response": {
                        "sql_query": (
                            "SELECT SUM(annual_premium) FROM policies"
                        ),
                        "database_executed": False,
                    },
                }

            return {
                "status": "rejected",
                "response": {
                    "error_code": "UNSUPPORTED_QUESTION",
                    "database_executed": False,
                },
            }

        if capability == "validate_sql":

            if payload.get("sql_query") == (
                "SELECT policy_id FROM policies"
            ):
                return {
                    "status": "success",
                    "response": {
                        "validation_passed": True,
                        "database_executed": False,
                    },
                }

            return {
                "status": "error",
                "response": {
                    "error_code": "UNSAFE_SQL",
                    "database_executed": False,
                },
            }

        raise ValueError("Unsupported capability")


class ExternalAgentAdapter:

    def __init__(self, manifest, transport):
        self.manifest = manifest
        self.transport = transport

    def execute(self, request, *, approved_run=False):

        if approved_run is not True:
            raise PermissionError(
                "Explicit test approval required"
            )

        if request.agent_id != self.manifest["agent_id"]:
            raise ValueError("Agent identity mismatch")

        if request.capability not in self.manifest["capabilities"]:
            raise ValueError("Capability not declared")

        if not isinstance(request.payload, dict):
            raise ValueError("Payload must be a dictionary")

        if not isinstance(self.transport, MockDatabricksTransport):
            raise PermissionError(
                "Only mock transport is supported in Phase 19.0"
            )

        result = self.transport.invoke(
            self.manifest["endpoint_name"],
            request.capability,
            request.payload,
        )

        if not isinstance(result, dict):
            raise ValueError("Invalid response")

        if result.get("status") not in {
            "success", "error", "rejected"
        }:
            raise ValueError("Invalid response status")

        if not isinstance(result.get("response"), dict):
            raise ValueError("Invalid response payload")

        return ExternalAgentResponse(
            agent_id=request.agent_id,
            capability=request.capability,
            status=result["status"],
            response=result["response"],
            execution_target="databricks_mock",
            endpoint_invoked=False,
        )
