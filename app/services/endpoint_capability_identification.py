"""HEAAP Phase 20.5 - Endpoint capability identification."""

import json
import re
from pathlib import Path

from app.services.automatic_agent_onboarding import (
    create_pending_onboarding_review,
)
from app.services.databricks_endpoint_inspector import (
    inspect_databricks_endpoints,
)


SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class EndpointCapabilityIdentificationService:

    def __init__(self, catalog_file, output_dir=None):
        self.catalog_file = Path(catalog_file)
        self.output_dir = Path(
            output_dir or "reports/phase20_5/onboarding"
        )

    def _load_catalog(self):
        with self.catalog_file.open(
            "r", encoding="utf-8-sig"
        ) as file:
            catalog = json.load(file)

        if (
            not isinstance(catalog, dict)
            or catalog.get("provider") != "databricks"
        ):
            raise ValueError("Invalid capability catalog")

        entries = catalog.get("entries")

        if not isinstance(entries, list):
            raise ValueError("Invalid catalog entries")

        mapping = {}

        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Invalid catalog entry")

            name = entry.get("endpoint_name")
            agent_id = entry.get("agent_id")
            capabilities = entry.get("declared_capabilities")

            if (
                not isinstance(name, str)
                or not SAFE_NAME.fullmatch(name)
                or not isinstance(agent_id, str)
                or not SAFE_NAME.fullmatch(agent_id)
                or not isinstance(capabilities, list)
                or not capabilities
                or not all(
                    isinstance(c, str)
                    and SAFE_NAME.fullmatch(c)
                    for c in capabilities
                )
                or len(capabilities) != len(set(capabilities))
            ):
                raise ValueError("Invalid capability declaration")

            if name in mapping:
                raise ValueError("Duplicate catalog endpoint")

            mapping[name] = entry

        return mapping

    def identify(self, endpoints):
        candidates = inspect_databricks_endpoints(endpoints)
        catalog = self._load_catalog()

        results = []

        for candidate in candidates:
            name = candidate["endpoint_name"]
            entry = catalog.get(name)

            if entry is None:
                results.append({
                    "endpoint_name": name,
                    "status": "quarantined",
                    "reason": "No capability declaration available",
                    "execution_authorized": False,
                    "automatically_registered": False,
                })
                continue

            discovery = {
                "provider": "databricks",
                "agent_id": entry["agent_id"],
                "endpoint_name": name,
                "declared_capabilities": entry[
                    "declared_capabilities"
                ],
            }

            onboarding = create_pending_onboarding_review(
                discovery,
                output_dir=self.output_dir,
            )

            results.append({
                "endpoint_name": name,
                "agent_id": entry["agent_id"],
                "status": "pending_manual_review",
                "declared_capabilities": entry[
                    "declared_capabilities"
                ],
                "capabilities_verified": False,
                "review_file": onboarding["review_file"],
                "manifest_file": onboarding["manifest_file"],
                "plan_file": onboarding["plan_file"],
                "planned_tests": onboarding[
                    "test_plan"
                ]["total_tests"],
                "execution_authorized": False,
                "automatically_registered": False,
            })

        return {
            "phase": "20.5",
            "total_endpoints": len(candidates),
            "pending_review": sum(
                r["status"] == "pending_manual_review"
                for r in results
            ),
            "quarantined": sum(
                r["status"] == "quarantined"
                for r in results
            ),
            "results": results,
            "live_endpoint_invoked": False,
            "production_approved": False,
        }
