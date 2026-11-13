
"""
HEAAP - Application Configuration

Loads environment variables for:
- Databricks Workspace
- Databricks SQL Warehouse
- Databricks Agent Discovery
- Local HEAAP services
"""

import os
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------
# Project directories
# ---------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE)


# ---------------------------------------
# Databricks configuration
# ---------------------------------------

DATABRICKS_HOST = (
    os.getenv("DATABRICKS_SERVER_HOSTNAME")
    or os.getenv("DATABRICKS_HOST")
    or ""
).strip().removeprefix("https://").removeprefix("http://").rstrip("/")

DATABRICKS_SERVER_HOSTNAME = DATABRICKS_HOST

DATABRICKS_TOKEN = (
    os.getenv("DATABRICKS_TOKEN") or ""
).strip()

DATABRICKS_HTTP_PATH = (
    os.getenv("DATABRICKS_HTTP_PATH") or ""
).strip()


# ---------------------------------------
# Databricks SQL configuration
# ---------------------------------------

DATABRICKS_CATALOG = os.getenv(
    "DATABRICKS_CATALOG",
    "agent_for_testing",
)

DATABRICKS_SCHEMA = os.getenv(
    "DATABRICKS_SCHEMA",
    "default",
)


# ---------------------------------------
# Agent discovery configuration
# ---------------------------------------

DATABRICKS_AGENT_ENDPOINT_ALLOWLIST = (
    os.getenv(
        "DATABRICKS_AGENT_ENDPOINT_ALLOWLIST",
        "",
    )
)

DATABRICKS_AGENT_CAPABILITY_MAP = (
    os.getenv(
        "DATABRICKS_AGENT_CAPABILITY_MAP",
        "{}",
    )
)


# ---------------------------------------
# Application configuration
# ---------------------------------------

APP_NAME = (
    "HEAAP - Hybrid Enterprise Agent Assurance Platform"
)

APP_VERSION = "1.1.0"

DEBUG = os.getenv(
    "DEBUG",
    "false",
).lower() == "true"


# ---------------------------------------
# Configuration validation
# ---------------------------------------

def validate_databricks_config(
    require_warehouse: bool = False,
) -> None:
    """
    Validate required Databricks configuration.

    Called before a Databricks operation rather
    than during module import.
    """

    missing = []

    if not DATABRICKS_HOST:
        missing.append(
            "DATABRICKS_SERVER_HOSTNAME"
        )

    if not DATABRICKS_TOKEN:
        missing.append(
            "DATABRICKS_TOKEN"
        )

    if require_warehouse and not DATABRICKS_HTTP_PATH:
        missing.append(
            "DATABRICKS_HTTP_PATH"
        )

    if missing:
        raise RuntimeError(
            "Missing Databricks configuration: "
            + ", ".join(missing)
        )
