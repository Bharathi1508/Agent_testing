"""HEAAP Phase 20.6 - Mock capability contract verification."""

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path


CONTRACTS = {
    "generate_sql": {
        "required_fields": ["sql"],
    },
    "validate_sql": {
        "required_fields": ["valid", "reason"],
    },
    "get_metadata": {
        "required_fields": ["columns"],
    },
    "detect_fraud": {
        "required_fields": ["fraud_score", "flagged"],
    },
}


def validate_response(capability, response):
    if capability not in CONTRACTS:
        return {
            "status": "UNSUPPORTED",
            "reason": "No registered contract",
        }

    if not isinstance(response, dict):
        return {
            "status": "FAIL",
            "reason": "Response must be a JSON object",
        }

    missing = [
        field
        for field in CONTRACTS[capability]["required_fields"]
        if field not in response
    ]

    if missing:
        return {
            "status": "FAIL",
            "reason": "Missing required fields: " + ", ".join(missing),
        }

    if capability == "generate_sql":
        sql = response["sql"]

        if not isinstance(sql, str) or not sql.strip():
            return {
                "status": "FAIL",
                "reason": "SQL must be a nonempty string",
            }

        # This is a basic contract check, not a SQL safety validator.
        if not sql.lstrip().upper().startswith("SELECT "):
            return {
                "status": "FAIL",
                "reason": "Expected a SELECT statement",
            }

    elif capability == "validate_sql":
        if type(response["valid"]) is not bool:
            return {
                "status": "FAIL",
                "reason": "valid must be boolean",
            }

        if not isinstance(response["reason"], str):
            return {
                "status": "FAIL",
                "reason": "reason must be a string",
            }

    elif capability == "get_metadata":
        columns = response["columns"]

        if not isinstance(columns, list):
            return {
                "status": "FAIL",
                "reason": "columns must be a list",
            }

        if not all(
            isinstance(column, dict)
            and isinstance(column.get("name"), str)
            and bool(column["name"].strip())
            and isinstance(column.get("data_type"), str)
            and bool(column["data_type"].strip())
            for column in columns
        ):
            return {
                "status": "FAIL",
                "reason": "Invalid metadata column structure",
            }

    elif capability == "detect_fraud":
        score = response["fraud_score"]

        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
            or not 0 <= score <= 1
        ):
            return {
                "status": "FAIL",
                "reason": "fraud_score must be a finite number from 0 to 1",
            }

        if type(response["flagged"]) is not bool:
            return {
                "status": "FAIL",
                "reason": "flagged must be boolean",
            }

    return {
        "status": "PASS",
        "reason": "Response satisfies the capability contract",
    }


class MockCapabilityTransport:
    """Offline-only transport. Never performs network calls."""

    def __init__(self, responses):
        self.responses = responses

    def invoke(self, agent_id, capability, payload):
        key = (agent_id, capability)

        if key not in self.responses:
            raise LookupError("Mock response not configured")

        response = self.responses[key]

        if callable(response):
            return response(payload)

        return response


class CapabilityContractVerifier:

    def __init__(self, transport):
        if not isinstance(transport, MockCapabilityTransport):
            raise TypeError(
                "Phase 20.6 requires MockCapabilityTransport"
            )
        self.transport = transport

    def verify(self, agent_id, capabilities, *, mock_run_authorized=False):
        if mock_run_authorized is not True:
            raise PermissionError(
                "Explicit mock-run authorization required"
            )

        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("Invalid agent ID")

        if (
            not isinstance(capabilities, list)
            or not capabilities
            or not all(isinstance(c, str) for c in capabilities)
            or len(capabilities) != len(set(capabilities))
        ):
            raise ValueError("Invalid capabilities")

        results = []

        for capability in capabilities:
            if capability not in CONTRACTS:
                results.append({
                    "capability": capability,
                    "status": "UNSUPPORTED",
                    "reason": "No registered contract",
                })
                continue

            try:
                response = self.transport.invoke(
                    agent_id,
                    capability,
                    {"test_mode": "offline_mock"},
                )

                validation = validate_response(
                    capability,
                    response,
                )

                results.append({
                    "capability": capability,
                    **validation,
                })

            except Exception as exc:
                results.append({
                    "capability": capability,
                    "status": "FAIL",
                    "reason": type(exc).__name__,
                })

        passed = sum(
            r["status"] == "PASS" for r in results
        )
        failed = sum(
            r["status"] == "FAIL" for r in results
        )
        unsupported = sum(
            r["status"] == "UNSUPPORTED" for r in results
        )

        verdict = (
            "PASS"
            if passed == len(results)
            else "FAIL"
            if failed
            else "UNSUPPORTED"
        )

        return {
            "phase": "20.6",
            "report_id": uuid.uuid4().hex,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "agent_id": agent_id,
            "execution_mode": "offline_mock",
            "capabilities_checked": len(results),
            "passed": passed,
            "failed": failed,
            "unsupported": unsupported,
            "verdict": verdict,
            "results": results,
            "governance": {
                "mock_run_authorized": True,
                "live_endpoint_invoked": False,
                "capabilities_independently_verified": False,
                "production_approved": False,
            },
        }


def save_contract_report(report, output_dir=None):
    directory = Path(
        output_dir or "reports/phase20_6"
    )
    directory.mkdir(parents=True, exist_ok=True)

    destination = directory / (
        report["report_id"] + ".json"
    )

    with destination.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    return str(destination)
