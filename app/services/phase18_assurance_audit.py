import hashlib
import hmac
import json
from pathlib import Path

AUDIT_DIR = Path("reports") / "phase18_6_audit"


def _validate_evidence_id(evidence_id):
    if (
        not isinstance(evidence_id, str)
        or len(evidence_id) != 32
        or any(c not in "0123456789abcdef" for c in evidence_id)
    ):
        raise ValueError("Invalid evidence ID")


def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def record_assurance_evidence(evidence):
    if not isinstance(evidence, dict):
        raise ValueError("Evidence must be an object")

    evidence_id = evidence.get("evidence_id")
    _validate_evidence_id(evidence_id)

    governance = evidence.get("governance", {})
    if (
        governance.get("production_approved") is not False
        or governance.get("database_execution_allowed") is not False
    ):
        raise ValueError("Invalid development-only governance")

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    evidence_path = AUDIT_DIR / f"{evidence_id}.json"
    digest_path = AUDIT_DIR / f"{evidence_id}.sha256"

    content = canonical_json(evidence)
    digest = hashlib.sha256(content).hexdigest()

    with evidence_path.open("xb") as file:
        file.write(content)

    try:
        with digest_path.open("x", encoding="ascii") as file:
            file.write(digest + "\n")
    except Exception:
        evidence_path.unlink(missing_ok=True)
        raise

    return {
        "evidence_path": str(evidence_path),
        "digest_path": str(digest_path),
        "sha256": digest,
    }


def verify_saved_evidence(evidence_id):
    _validate_evidence_id(evidence_id)

    evidence_path = AUDIT_DIR / f"{evidence_id}.json"
    digest_path = AUDIT_DIR / f"{evidence_id}.sha256"

    content = evidence_path.read_bytes()
    expected = digest_path.read_text(
        encoding="ascii"
    ).strip()

    actual = hashlib.sha256(content).hexdigest()

    return {
        "evidence_id": evidence_id,
        "verified": hmac.compare_digest(actual, expected),
        "expected_sha256": expected,
        "actual_sha256": actual,
    }
