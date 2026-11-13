import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class RealAgentEvidenceCollector:

    def __init__(self, output_dir=None):
        self.output_dir = Path(
            output_dir or "reports/phase22_20/evidence"
        )

    def collect(
        self,
        *,
        agent_id,
        test_id,
        request,
        response,
        execution_status,
        duration_ms,
        approved_execution,
        execution_id=None,
        endpoint=None,
        reference_fingerprint=None,
        source_type="unverified",
    ):
        if not approved_execution:
            raise PermissionError(
                "Evidence collection requires "
                "an approved execution"
            )

        if source_type not in {
            "simulated",
            "real_agent",
            "unverified",
        }:
            raise ValueError("Invalid source_type")

        if not agent_id or not test_id:
            raise ValueError(
                "agent_id and test_id are required"
            )

        if duration_ms < 0:
            raise ValueError(
                "duration_ms cannot be negative"
            )

        evidence = {
            "evidence_id": str(uuid.uuid4()),
            "phase": "22.20",
            "component": "real_agent_evidence_collector",
            "collected_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "agent_id": agent_id,
            "test_id": test_id,
            "execution_id": execution_id,
            "endpoint": endpoint,
            "source_type": source_type,
            "provenance_verified_by_collector": False,
            "approved_execution_asserted": True,
            "execution_status": execution_status,
            "duration_ms": duration_ms,
            "request": request,
            "response": response,
            "reference_fingerprint": reference_fingerprint,
        }

        canonical = json.dumps(
            evidence,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        evidence["fingerprint"] = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        return evidence

    def save(self, evidence):
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        evidence_id = evidence["evidence_id"]

        uuid.UUID(evidence_id)

        path = self.output_dir / (
            f"evidence_{evidence_id}.json"
        )

        with path.open(
            "x", encoding="utf-8"
        ) as file:
            json.dump(
                evidence,
                file,
                indent=2,
                default=str,
            )

        return str(path)
