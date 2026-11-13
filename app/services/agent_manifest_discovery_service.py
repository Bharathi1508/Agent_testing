"""HEAAP Phase 22.1 - Read-only manifest discovery."""

import json
from pathlib import Path

from app.services.external_agent_manifest_validator import (
    validate_external_manifest,
)


class AgentManifestDiscoveryService:

    def __init__(self, discovery_dir="reports/discovered_agents"):
        self.discovery_dir = Path(discovery_dir)

    def discover(self):
        """Discover and validate local candidate manifests.

        Does not register, approve, or execute agents.
        """

        candidates = []

        if not self.discovery_dir.exists():
            return candidates

        for manifest_file in sorted(
            self.discovery_dir.glob("*.json")
        ):
            try:
                with manifest_file.open(
                    "r", encoding="utf-8-sig"
                ) as file:
                    manifest = json.load(file)

                validated = validate_external_manifest(
                    manifest
                )

                candidates.append({
                    "agent_id": validated["agent_id"],
                    "name": validated["name"],
                    "framework": validated["framework"],
                    "endpoint_name": validated["endpoint_name"],
                    "declared_capabilities": validated[
                        "declared_capabilities"
                    ],
                    "manifest_valid": True,
                    "capabilities_verified": False,
                    "trust_status": "unverified",
                    "production_approved": False,
                    "discovery_status": "pending_review",
                    "source_file": manifest_file.name,
                })

            except (ValueError, TypeError, OSError, json.JSONDecodeError) as exc:
                candidates.append({
                    "source_file": manifest_file.name,
                    "manifest_valid": False,
                    "discovery_status": "invalid_manifest",
                    "error": str(exc),
                })

        return candidates
