
import hashlib
import json
import sqlite3

from datetime import datetime, timezone
from pathlib import Path


# ==========================================================
# 1. DATABASE CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "governance.db"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    return conn


# ==========================================================
# 2. DATABASE INITIALIZATION
# ==========================================================

def init_db():

    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS assurance_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                status TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                agent_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                approved_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                revoked_by TEXT,
                revoked_at TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS governance_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                fingerprint TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_assurance_agent_id
            ON assurance_runs(agent_id, id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_governance_history_agent_id
            ON governance_history(agent_id, id)
        """)


# ==========================================================
# 3. MANIFEST FINGERPRINT
# ==========================================================

def manifest_fingerprint(manifest):
    """
    Generate a deterministic fingerprint for an agent.

    Lifecycle status is excluded because changing an
    agent from inactive to active should not invalidate
    its governance approval.
    """

    if hasattr(manifest, "model_dump"):

        data = manifest.model_dump(mode="json")

    elif isinstance(manifest, dict):

        data = dict(manifest)

    else:

        raise TypeError(
            "Manifest must be a Pydantic model or dictionary"
        )

    # Exclude mutable lifecycle fields
    data.pop("status", None)

    canonical_json = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        default=str
    )

    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()


# ==========================================================
# 4. SAVE ASSURANCE RESULTS
# ==========================================================

def save_assurance_run(agent_id, report):
    """
    Save an assurance report into SQLite.
    """

    if hasattr(report, "model_dump"):

        report = report.model_dump(mode="json")

    else:

        report = dict(report)

    fingerprint = report.get("fingerprint")
    status = report.get("status")

    if not fingerprint:
        raise ValueError(
            "Assurance report is missing fingerprint"
        )

    if not status:
        raise ValueError(
            "Assurance report is missing status"
        )

    report_json = json.dumps(
        report,
        default=str
    )

    with get_connection() as conn:

        conn.execute("""
            INSERT INTO assurance_runs (
                agent_id,
                fingerprint,
                status,
                report_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            agent_id,
            fingerprint,
            status,
            report_json,
            utc_now()
        ))


def save_assurance(manifest, report):
    """
    Called by assurance_engine.py.

    Adds the manifest fingerprint and persists
    the completed assurance report.
    """

    if hasattr(report, "model_dump"):

        report = report.model_dump(mode="json")

    else:

        report = dict(report)

    report["agent_id"] = manifest.agent_id

    report["fingerprint"] = manifest_fingerprint(
        manifest
    )

    save_assurance_run(
        manifest.agent_id,
        report
    )

    return report


# ==========================================================
# 5. RETRIEVE LATEST ASSURANCE
# ==========================================================

def latest_assurance(agent_id):
    """
    Retrieve the most recent assurance result.
    """

    with get_connection() as conn:

        row = conn.execute("""
            SELECT *
            FROM assurance_runs
            WHERE agent_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (agent_id,)).fetchone()

    if row is None:
        return None

    result = dict(row)

    result["report"] = json.loads(
        result["report_json"]
    )

    return result


# ==========================================================
# 6. SAVE GOVERNANCE APPROVAL
# ==========================================================

def save_approval(manifest, reviewer):
    """
    Save or renew an approval for an agent.

    Approval is only allowed by approval_service.py
    after successful assurance validation.
    """

    fingerprint = manifest_fingerprint(
        manifest
    )

    timestamp = utc_now()

    with get_connection() as conn:

        conn.execute("""
            INSERT INTO approvals (
                agent_id,
                fingerprint,
                reviewer,
                approved_at,
                revoked,
                revoked_by,
                revoked_at
            )
            VALUES (?, ?, ?, ?, 0, NULL, NULL)

            ON CONFLICT(agent_id)
            DO UPDATE SET
                fingerprint = excluded.fingerprint,
                reviewer = excluded.reviewer,
                approved_at = excluded.approved_at,
                revoked = 0,
                revoked_by = NULL,
                revoked_at = NULL
        """, (
            manifest.agent_id,
            fingerprint,
            reviewer,
            timestamp
        ))

        conn.execute("""
            INSERT INTO governance_history (
                agent_id,
                event_type,
                reviewer,
                fingerprint,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            manifest.agent_id,
            "approved",
            reviewer,
            fingerprint,
            timestamp
        ))


# ==========================================================
# 7. GET GOVERNANCE APPROVAL
# ==========================================================

def get_approval(agent_id):
    """
    Retrieve the current approval record.
    """

    with get_connection() as conn:

        row = conn.execute("""
            SELECT *
            FROM approvals
            WHERE agent_id = ?
        """, (agent_id,)).fetchone()

    if row is None:
        return None

    return dict(row)


# ==========================================================
# 8. REVOKE GOVERNANCE APPROVAL
# ==========================================================

def revoke_approval(agent_id, reviewer):
    """
    Revoke an existing governance approval.
    """

    timestamp = utc_now()

    with get_connection() as conn:

        conn.execute("""
            UPDATE approvals
            SET
                revoked = 1,
                revoked_by = ?,
                revoked_at = ?
            WHERE agent_id = ?
        """, (
            reviewer,
            timestamp,
            agent_id
        ))

        conn.execute("""
            INSERT INTO governance_history (
                agent_id,
                event_type,
                reviewer,
                fingerprint,
                created_at
            )
            VALUES (?, ?, ?, NULL, ?)
        """, (
            agent_id,
            "rejected",
            reviewer,
            timestamp
        ))


# ==========================================================
# 9. GOVERNANCE HISTORY
# ==========================================================

def get_history(agent_id):
    """
    Retrieve approval and rejection events.
    """

    with get_connection() as conn:

        rows = conn.execute("""
            SELECT
                id,
                agent_id,
                event_type,
                reviewer,
                fingerprint,
                created_at
            FROM governance_history
            WHERE agent_id = ?
            ORDER BY id DESC
        """, (agent_id,)).fetchall()

    return [
        dict(row)
        for row in rows
    ]


# ==========================================================
# 10. INITIALIZE SQLITE DATABASE
# ==========================================================

init_db()
