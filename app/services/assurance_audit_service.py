"""
HEAAP Phase 17.6
Local audit evidence persistence.

Development-only local files.
Not a tamper-proof or transactional audit database.
"""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.assurance_evidence_service import (
    assess_assurance_evidence,
    evidence_hash,
    canonical_json,
)


AUDIT_DIR = Path("reports") / "phase17_6_audit"

SAFE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,127}$")


def write_new_json(path, content):

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("x", encoding="utf-8") as file:
        json.dump(
            content,
            file,
            indent=4,
            ensure_ascii=False,
            allow_nan=False,
        )

    return path


def record_assurance_evidence(report):

    assessment = assess_assurance_evidence(report)

    agent_id = report["agent_id"]

    if not SAFE_ID.fullmatch(agent_id):
        raise ValueError("Unsafe agent ID")

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%S_%fZ")

    record_id = (
        f"{timestamp}_{uuid.uuid4().hex}"
    )

    evidence_path = AUDIT_DIR / (
        f"{agent_id}_{record_id}_evidence.json"
    )

    audit_path = AUDIT_DIR / (
        f"{agent_id}_{record_id}_audit.json"
    )

    evidence = {
        "record_id": record_id,
        "agent_id": agent_id,
        "evidence_sha256": evidence_hash(report),
        "report": report,
    }

    audit = {
        "record_id": record_id,
        "agent_id": agent_id,
        "event_type": "ASSURANCE_EVIDENCE_RECORDED",
        "recorded_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "evidence_sha256": evidence["evidence_sha256"],
        "governance": assessment,
    }

    write_new_json(evidence_path, evidence)
    write_new_json(audit_path, audit)

    return {
        "record_id": record_id,
        "evidence_path": str(evidence_path),
        "audit_path": str(audit_path),
        "governance": assessment,
    }


def verify_saved_evidence(evidence_path, audit_path):

    evidence = json.loads(
        Path(evidence_path).read_text(encoding="utf-8-sig")
    )

    audit = json.loads(
        Path(audit_path).read_text(encoding="utf-8-sig")
    )

    report = evidence["report"]

    recalculated = evidence_hash(report)

    if evidence["record_id"] != audit["record_id"]:
        return False

    if evidence["agent_id"] != audit["agent_id"]:
        return False

    if recalculated != evidence["evidence_sha256"]:
        return False

    if recalculated != audit["evidence_sha256"]:
        return False

    governance = audit["governance"]

    if governance["evidence_sha256"] != recalculated:
        return False

    return True
