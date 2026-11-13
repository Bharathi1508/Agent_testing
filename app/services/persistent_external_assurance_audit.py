"""HEAAP Phase 19.4 - Persistent Assurance Audit."""

import hashlib
import json
import sqlite3
import uuid

from contextlib import contextmanager
from pathlib import Path


DB_PATH = Path("reports/phase19_4/heaap_audit.db")


def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


class PersistentExternalAssuranceAudit:

    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)

        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS assurance_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def save_report(self, report):
        if not isinstance(report, dict):
            raise ValueError("Report must be a dictionary")

        agent_id = report.get("agent_id")

        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("Invalid agent_id")

        report_json = canonical_json(report)

        digest = hashlib.sha256(
            report_json.encode("utf-8")
        ).hexdigest()

        evidence_id = uuid.uuid4().hex

        with self._connect() as connection:
            connection.execute("""
                INSERT INTO assurance_evidence
                    (evidence_id, agent_id, report_json, sha256)
                VALUES (?, ?, ?, ?)
            """, (
                evidence_id,
                agent_id,
                report_json,
                digest,
            ))

        return evidence_id

    def verify_report(self, evidence_id):
        with self._connect() as connection:
            row = connection.execute("""
                SELECT report_json, sha256
                FROM assurance_evidence
                WHERE evidence_id = ?
            """, (evidence_id,)).fetchone()

        if row is None:
            raise LookupError("Evidence not found")

        report_json, expected_digest = row

        actual_digest = hashlib.sha256(
            report_json.encode("utf-8")
        ).hexdigest()

        return actual_digest == expected_digest

    def get_report(self, evidence_id):
        if not self.verify_report(evidence_id):
            raise ValueError("Evidence integrity check failed")

        with self._connect() as connection:
            row = connection.execute("""
                SELECT report_json
                FROM assurance_evidence
                WHERE evidence_id = ?
            """, (evidence_id,)).fetchone()

        return json.loads(row[0])

    def list_reports(self, agent_id=None):
        with self._connect() as connection:
            if agent_id is None:
                rows = connection.execute("""
                    SELECT evidence_id, agent_id, created_at
                    FROM assurance_evidence
                    ORDER BY created_at DESC, evidence_id DESC
                """).fetchall()
            else:
                rows = connection.execute("""
                    SELECT evidence_id, agent_id, created_at
                    FROM assurance_evidence
                    WHERE agent_id = ?
                    ORDER BY created_at DESC, evidence_id DESC
                """, (agent_id,)).fetchall()

        return [
            {
                "evidence_id": row[0],
                "agent_id": row[1],
                "created_at": row[2],
            }
            for row in rows
        ]
