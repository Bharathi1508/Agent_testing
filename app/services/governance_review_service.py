"""HEAAP 21.8 - Local governance review and audit."""

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
DECISIONS = {"approved_for_next_stage", "rejected"}


class GovernanceReviewService:

    def __init__(
        self,
        reviews_dir="reports/phase18_9_onboarding",
        db_path="reports/governance/reviews.db",
    ):
        self.reviews_dir = Path(reviews_dir).resolve()
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(
            str(self.db_path), timeout=10
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        con = self._connect()
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS governance_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_id TEXT NOT NULL UNIQUE,
                    reviewer TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    review_sha256 TEXT NOT NULL,
                    decided_at TEXT NOT NULL
                )
            """)
            con.commit()
        finally:
            con.close()

    def _review_path(self, review_id):
        if not SAFE_ID.fullmatch(review_id):
            raise ValueError("Invalid review ID")
        return self.reviews_dir / (review_id + ".json")

    def get_review(self, review_id):
        path = self._review_path(review_id)
        if not path.is_file():
            return None

        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("Invalid review JSON")

        import hashlib
        digest = hashlib.sha256(raw).hexdigest()
        return data, digest

    def get_decision(self, review_id):
        self._review_path(review_id)
        con = self._connect()
        try:
            row = con.execute(
                "SELECT * FROM governance_decisions "
                "WHERE review_id = ?",
                (review_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            con.close()

    def list_reviews(self):
        if not self.reviews_dir.is_dir():
            return []

        result = []
        for path in sorted(self.reviews_dir.glob("*.json")):
            if not SAFE_ID.fullmatch(path.stem):
                continue
            try:
                loaded = self.get_review(path.stem)
                if loaded is None:
                    continue
                data, digest = loaded
            except (OSError, ValueError, UnicodeError):
                continue

            result.append({
                "review_id": path.stem,
                "agent_id": data.get("agent_id"),
                "onboarding_status": data.get(
                    "onboarding_status",
                    data.get("status", "unknown")
                ),
                "decision": self.get_decision(path.stem),
                "source_sha256": digest,
            })
        return result

    def record_decision(
        self, review_id, reviewer, decision, reason,
        expected_sha256,
    ):
        if decision not in DECISIONS:
            raise ValueError("Unsupported decision")

        if not isinstance(reviewer, str) or not (
            3 <= len(reviewer.strip()) <= 128
        ):
            raise ValueError("Invalid reviewer")

        if not isinstance(reason, str) or not (
            10 <= len(reason.strip()) <= 2000
        ):
            raise ValueError("Reason must contain 10-2000 characters")

        loaded = self.get_review(review_id)
        if loaded is None:
            raise ValueError("Review not found")

        data, digest = loaded

        if digest != expected_sha256:
            raise ValueError("Review evidence has changed")

        status = data.get(
            "onboarding_status",
            data.get("status")
        )
        if status != "pending_manual_review":
            raise ValueError("Review is not pending manual review")

        timestamp = datetime.now(timezone.utc).isoformat()

        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            con.execute("""
                INSERT INTO governance_decisions
                (review_id, reviewer, decision, reason,
                 review_sha256, decided_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                review_id,
                reviewer.strip(),
                decision,
                reason.strip(),
                digest,
                timestamp,
            ))
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            raise ValueError("Review already has a decision")
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

        return self.get_decision(review_id)
