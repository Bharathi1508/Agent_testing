"""Phase 18.9 - Review-only external agent onboarding."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services.external_agent_manifest_validator import (
    validate_external_manifest,
)


REVIEW_DIR = Path("reports") / "phase18_9_onboarding"


def prepare_external_onboarding(manifest, discovery):
    validated = validate_external_manifest(manifest)

    if not isinstance(discovery, dict):
        raise ValueError("Invalid discovery result")

    if discovery.get("source") != "databricks":
        raise ValueError("Unsupported discovery source")

    if validated["framework"] != "databricks":
        raise ValueError("Framework and source mismatch")

    candidates = discovery.get("candidates")

    if not isinstance(candidates, list):
        raise ValueError("Invalid candidates")

    matches = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict)
        and candidate.get("endpoint_name")
        == validated["endpoint_name"]
    ]

    if len(matches) != 1:
        raise ValueError(
            "Exactly one matching endpoint is required"
        )

    candidate = matches[0]

    if candidate.get("provider") != "databricks":
        raise ValueError("Provider mismatch")

    if candidate.get("candidate_type") != (
        "unverified_serving_endpoint"
    ):
        raise ValueError("Unexpected candidate type")

    return {
        "review_id": uuid4().hex,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "phase": "18.9",
        "agent": validated,
        "discovered_endpoint": {
            "provider": "databricks",
            "endpoint_name": validated["endpoint_name"],
        },
        "review_status": "pending_manual_review",
        "execution_authorized": False,
        "automatically_registered": False,
        "production_approved": False,
    }


def save_onboarding_review(review):
    if not isinstance(review, dict):
        raise ValueError("Invalid review")

    if (
        review.get("review_status")
        != "pending_manual_review"
        or review.get("execution_authorized") is not False
        or review.get("automatically_registered") is not False
        or review.get("production_approved") is not False
    ):
        raise ValueError("Invalid onboarding governance")

    review_id = review.get("review_id")

    if (
        not isinstance(review_id, str)
        or len(review_id) != 32
        or any(
            c not in "0123456789abcdef"
            for c in review_id
        )
    ):
        raise ValueError("Invalid review ID")

    REVIEW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = REVIEW_DIR / f"{review_id}.json"

    with path.open("x", encoding="utf-8") as file:
        json.dump(review, file, indent=2)

    return str(path)
