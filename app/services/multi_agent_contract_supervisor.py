"""HEAAP Phase 20.7 - Multi-agent contract assurance supervisor."""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.capability_contract_verifier import (
    CapabilityContractVerifier,
    MockCapabilityTransport,
)


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class MultiAgentContractSupervisor:
    """Offline mock-only multi-agent assurance coordinator."""

    def __init__(self, transport):
        if not isinstance(transport, MockCapabilityTransport):
            raise TypeError("Mock transport required")
        self.verifier = CapabilityContractVerifier(transport)

    @staticmethod
    def _validate_manifest(manifest):
        if not isinstance(manifest, dict):
            raise ValueError("Manifest must be an object")

        agent_id = manifest.get("agent_id")
        capabilities = manifest.get("capabilities")

        if (
            not isinstance(agent_id, str)
            or not SAFE_ID.fullmatch(agent_id)
        ):
            raise ValueError("Invalid agent ID")

        if (
            not isinstance(capabilities, list)
            or not capabilities
            or not all(
                isinstance(cap, str)
                and SAFE_ID.fullmatch(cap)
                for cap in capabilities
            )
            or len(capabilities) != len(set(capabilities))
        ):
            raise ValueError("Invalid capability declaration")

        return agent_id, capabilities

    def run(self, manifests, *, mock_run_authorized=False):
        if mock_run_authorized is not True:
            raise PermissionError(
                "Explicit mock-run authorization required"
            )

        if not isinstance(manifests, list) or not manifests:
            raise ValueError("Nonempty manifest list required")

        validated = []
        seen = set()

        # Validate the entire batch before invoking any mock.
        for manifest in manifests:
            agent_id, capabilities = self._validate_manifest(
                manifest
            )

            if agent_id in seen:
                raise ValueError("Duplicate agent ID")

            seen.add(agent_id)
            validated.append((agent_id, capabilities))

        results = []

        for agent_id, capabilities in validated:
            result = self.verifier.verify(
                agent_id,
                capabilities,
                mock_run_authorized=True,
            )
            results.append(result)

        passed = sum(
            result["verdict"] == "PASS"
            for result in results
        )
        failed = sum(
            result["verdict"] == "FAIL"
            for result in results
        )
        unsupported = sum(
            result["verdict"] == "UNSUPPORTED"
            for result in results
        )

        overall_verdict = (
            "PASS"
            if passed == len(results)
            else "FAIL"
            if failed
            else "UNSUPPORTED"
        )

        return {
            "phase": "20.7",
            "report_id": uuid.uuid4().hex,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "execution_mode": "offline_mock",
            "total_agents": len(results),
            "passed_agents": passed,
            "failed_agents": failed,
            "unsupported_agents": unsupported,
            "overall_verdict": overall_verdict,
            "agents": results,
            "governance": {
                "mock_run_authorized": True,
                "live_endpoint_invoked": False,
                "independent_approval_verified": False,
                "production_approved": False,
            },
        }


def save_multi_agent_contract_report(report, output_dir=None):
    directory = Path(
        output_dir or "reports/phase20_7"
    )
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / (report["report_id"] + ".json")

    with path.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    return str(path)
