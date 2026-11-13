"""HEAAP Phase 20.4 - Read-only Databricks discovery."""

import os
from pathlib import Path
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv


class DatabricksReadOnlyDiscoveryProvider:

    def __init__(self, host=None, token=None, allowed_hosts=None):

        load_dotenv(
            dotenv_path=Path.cwd() / ".env"
        )

        raw_host = (
            host
            or os.getenv("DATABRICKS_HOST")
            or os.getenv("DATABRICKS_SERVER_HOSTNAME")
        )

        self.token = token or os.getenv("DATABRICKS_TOKEN")

        if not raw_host:
            raise ValueError("Databricks host is missing")

        if not self.token:
            raise ValueError("Databricks token is missing")

        if "://" not in raw_host:
            raw_host = "https://" + raw_host

        parsed = urlsplit(raw_host)

        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid Databricks workspace URL")

        hostname = parsed.hostname.lower()

        if allowed_hosts is None:
            allowed_hosts = os.getenv(
                "HEAAP_ALLOWED_DATABRICKS_HOSTS", ""
            ).split(",")

        allowlist = {
            item.strip().lower()
            for item in allowed_hosts
            if isinstance(item, str) and item.strip()
        }

        if hostname not in allowlist:
            raise PermissionError(
                "Databricks host is not allowlisted"
            )

        self.host = "https://" + hostname

    def discover(self):
        url = self.host + "/api/2.0/serving-endpoints"

        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            },
            timeout=20,
            allow_redirects=False,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError("Invalid Databricks API response")

        endpoints = payload.get("endpoints", [])

        if not isinstance(endpoints, list):
            raise ValueError("Invalid endpoint collection")

        return endpoints
