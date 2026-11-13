"""HEAAP Phase 21.3 - Read-only onboarding monitoring."""

import json
from pathlib import Path


class OnboardingMonitoringService:

    def __init__(self, reports_root="reports"):
        self.root = Path(reports_root).resolve()

    def list_candidates(self):
        candidates = []

        if not self.root.is_dir():
            return candidates

        folders = [
            "phase20_2",
            "phase20_3",
            "phase20_5",
        ]

        for folder in folders:
            directory = self.root / folder

            if not directory.is_dir():
                continue

            for path in directory.rglob("*.json"):
                try:
                    with path.open(
                        "r", encoding="utf-8-sig"
                    ) as file:
                        data = json.load(file)
                except (OSError, ValueError, UnicodeError):
                    continue

                if not isinstance(data, dict):
                    continue

                agent_id = data.get("agent_id")

                if not isinstance(agent_id, str):
                    continue

                status = data.get(
                    "status",
                    data.get(
                        "onboarding_status",
                        "unknown",
                    ),
                )

                candidates.append({
                    "agent_id": agent_id,
                    "endpoint_name": data.get(
                        "endpoint_name"
                    ),
                    "provider": data.get(
                        "provider", "unknown"
                    ),
                    "status": status,
                    "declared_capabilities": data.get(
                        "declared_capabilities",
                        [],
                    ),
                    "source_phase": folder,
                    "execution_authorized": False,
                    "production_approved": False,
                })

        return candidates

    def get_summary(self):
        candidates = self.list_candidates()

        return {
            "total_candidates": len(candidates),
            "pending_review": sum(
                item["status"] == "pending_manual_review"
                for item in candidates
            ),
            "quarantined": sum(
                item["status"] == "quarantined"
                for item in candidates
            ),
            "unknown": sum(
                item["status"] not in (
                    "pending_manual_review",
                    "quarantined",
                )
                for item in candidates
            ),
        }
