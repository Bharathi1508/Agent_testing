"""HEAAP Phase 22.4 - Read-only Databricks endpoint discovery."""

import os
import re

import httpx


class DatabricksAgentDiscoveryService:

    def __init__(self):
        self.host = os.getenv("DATABRICKS_HOST", "").rstrip("/")
        self.token = os.getenv("DATABRICKS_TOKEN", "")

        if not self.host.startswith("https://"):
            raise ValueError("Valid DATABRICKS_HOST is required")

        if not self.token:
            raise ValueError("DATABRICKS_TOKEN is required")

    def discover(self):
        """List serving endpoints without invoking them."""

        url = f"{self.host}/api/2.0/serving-endpoints"

        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                url,
                headers={
                    "Authorization": f"Bearer {self.token}"
                },
            )
            response.raise_for_status()
            payload = response.json()

        endpoints = payload.get("endpoints", [])

        candidates = []

        for endpoint in endpoints:
            name = endpoint.get("name")

            if not isinstance(name, str):
                continue

            candidates.append({
                "endpoint_name": name,
                "source": "databricks",
                "discovery_status": "requires_classification",
                "capabilities_verified": False,
                "trust_status": "unverified",
                "production_approved": False,
                "automatically_registered": False,
                "live_endpoint_invoked": False,
            })

        return candidates
