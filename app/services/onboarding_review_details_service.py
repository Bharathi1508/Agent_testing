"""HEAAP Phase 21.4 - Read-only onboarding review details."""

import json
import re
from pathlib import Path


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class OnboardingReviewDetailsService:

    def __init__(
        self,
        reports_dir="reports/phase18_9_onboarding",
    ):
        self.reports_dir = Path(reports_dir).resolve()

    def list_reviews(self):
        if not self.reports_dir.is_dir():
            return []

        reviews = []

        for path in sorted(self.reports_dir.glob("*.json")):
            try:
                with path.open(
                    "r", encoding="utf-8-sig"
                ) as file:
                    data = json.load(file)
            except (OSError, ValueError, UnicodeError):
                continue

            if not isinstance(data, dict):
                continue

            reviews.append({
                "review_id": path.stem,
                "agent_id": data.get("agent_id"),
                "status": data.get(
                    "status",
                    data.get(
                        "onboarding_status", "unknown"
                    ),
                ),
                "execution_authorized": (
                    data.get("execution_authorized") is True
                ),
                "production_approved": (
                    data.get("production_approved") is True
                ),
            })

        return reviews

    def get_review(self, review_id):
        if not SAFE_ID.fullmatch(review_id):
            raise ValueError("Invalid review ID")

        path = self.reports_dir / f"{review_id}.json"

        if not path.is_file():
            return None

        with path.open(
            "r", encoding="utf-8-sig"
        ) as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Invalid review document")

        return {
            "review_id": review_id,
            "record": data,
            "governance": {
                "read_only": True,
                "approval_performed": False,
                "execution_performed": False,
            },
        }
