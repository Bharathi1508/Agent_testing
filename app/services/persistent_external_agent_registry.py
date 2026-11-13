from contextlib import contextmanager
"""Phase 19.4 - Persistent registry for external agent manifests."""

import json
import sqlite3
from pathlib import Path

from app.services.external_agent_approval_gate import (
    load_onboarding_review,
    validate_onboarding_approval,
)


DB_PATH = Path("reports/phase19_4/heaap_registry.db")


class PersistentExternalAgentRegistry:

    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=10
        )
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
                CREATE TABLE IF NOT EXISTS external_agents (
                    agent_id TEXT PRIMARY KEY,
                    manifest_json TEXT NOT NULL,
                    review_file TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def register_agent(self, manifest, review_file):
        review = load_onboarding_review(review_file)
        validate_onboarding_approval(review, manifest)

        agent_id = manifest["agent_id"]

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO external_agents
                    (agent_id, manifest_json, review_file)
                VALUES (?, ?, ?)
                """,
                (
                    agent_id,
                    json.dumps(manifest, sort_keys=True),
                    str(Path(review_file).resolve()),
                ),
            )

        return agent_id

    def get_agent(self, agent_id):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT manifest_json, review_file
                FROM external_agents
                WHERE agent_id = ?
                """,
                (agent_id,),
            ).fetchone()

        if row is None:
            raise LookupError("Agent not registered")

        manifest = json.loads(row[0])
        review = load_onboarding_review(row[1])

        # A changed or revoked review must block subsequent runs.
        validate_onboarding_approval(review, manifest)

        return {
            "manifest": manifest,
            "review": review,
        }

    def list_agents(self):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT agent_id FROM external_agents ORDER BY agent_id"
            ).fetchall()

        return [row[0] for row in rows]

