"""HEAAP Phase 20.3 - Offline endpoint discovery provider."""

import json
from pathlib import Path


class OfflineEndpointDiscoveryProvider:
    def __init__(self, discovery_file):
        self.discovery_file = Path(discovery_file)

    def discover(self):
        with self.discovery_file.open(
            "r", encoding="utf-8"
        ) as file:
            payload = json.load(file)

        if not isinstance(payload, dict):
            raise ValueError("Discovery payload must be an object")

        endpoints = payload.get("endpoints")

        if not isinstance(endpoints, list):
            raise ValueError("Endpoints must be a list")

        return endpoints
