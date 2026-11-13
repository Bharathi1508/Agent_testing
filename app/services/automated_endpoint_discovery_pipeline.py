"""HEAAP Phase 20.3 - Automated discovery and onboarding."""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.services.automatic_agent_onboarding import (
    create_pending_onboarding_review,
    validate_discovery_metadata,
)


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def discovery_fingerprint(metadata):
    return hashlib.sha256(
        canonical_json(metadata).encode("utf-8")
    ).hexdigest()


class AutomatedEndpointDiscoveryPipeline:
    def __init__(self, provider, output_dir=None):
        self.provider = provider
        self.output_dir = Path(
            output_dir or "reports/phase20_3"
        )
        self.output_dir.mkdir(
            parents=True, exist_ok=True
        )
        self.index_file = self.output_dir / "candidate_index.json"

    def _load_index(self):
        if not self.index_file.exists():
            return {}

        with self.index_file.open(
            "r", encoding="utf-8"
        ) as file:
            index = json.load(file)

        if not isinstance(index, dict):
            raise ValueError("Invalid candidate index")

        return index

    def _save_index(self, index):
        temporary = self.output_dir / (
            "candidate_index." + uuid.uuid4().hex + ".tmp"
        )

        with temporary.open("x", encoding="utf-8") as file:
            json.dump(index, file, indent=2)

        os.replace(temporary, self.index_file)

    def run_discovery(self):
        endpoints = self.provider.discover()

        if not isinstance(endpoints, list):
            raise ValueError("Provider returned invalid endpoints")

        index = self._load_index()
        results = []

        seen = set()

        for endpoint in endpoints:
            try:
                normalized = validate_discovery_metadata(
                    endpoint
                )

                identity = (
                    normalized["provider"]
                    + ":"
                    + normalized["agent_id"]
                )

                if identity in seen:
                    raise ValueError(
                        "Duplicate agent in discovery batch"
                    )

                seen.add(identity)

                fingerprint = discovery_fingerprint(
                    normalized
                )

                previous = index.get(identity)

                if (
                    isinstance(previous, dict)
                    and previous.get("fingerprint") == fingerprint
                ):
                    results.append({
                        "identity": identity,
                        "status": "unchanged",
                        "review_file": previous.get(
                            "review_file"
                        ),
                    })
                    continue

                # New or changed metadata always creates
                # a fresh pending onboarding review.
                onboarding = create_pending_onboarding_review(
                    normalized,
                    output_dir=self.output_dir / "onboarding",
                )

                status = (
                    "changed"
                    if previous is not None
                    else "new"
                )

                index[identity] = {
                    "fingerprint": fingerprint,
                    "review_file": onboarding["review_file"],
                    "manifest_file": onboarding["manifest_file"],
                    "plan_file": onboarding["plan_file"],
                    "review_status": "pending_manual_review",
                }

                results.append({
                    "identity": identity,
                    "status": status,
                    "review_file": onboarding["review_file"],
                    "planned_tests": onboarding[
                        "test_plan"
                    ]["total_tests"],
                })

            except Exception as exc:
                results.append({
                    "identity": (
                        endpoint.get("agent_id", "unknown")
                        if isinstance(endpoint, dict)
                        else "unknown"
                    ),
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })

        self._save_index(index)

        summary = {
            "phase": "20.3",
            "run_id": uuid.uuid4().hex,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total_discovered": len(endpoints),
            "new": sum(
                r["status"] == "new" for r in results
            ),
            "changed": sum(
                r["status"] == "changed" for r in results
            ),
            "unchanged": sum(
                r["status"] == "unchanged" for r in results
            ),
            "errors": sum(
                r["status"] == "error" for r in results
            ),
            "results": results,
            "governance": {
                "automatically_approved": False,
                "automatically_registered": False,
                "live_endpoint_invoked": False,
                "production_approved": False,
            },
        }

        report_file = self.output_dir / (
            "discovery_" + summary["run_id"] + ".json"
        )

        with report_file.open("x", encoding="utf-8") as file:
            json.dump(summary, file, indent=2)

        summary["report_file"] = str(report_file)

        return summary
