
"""
HEAAP - Phase 13, Step 8

Local JSON Test Report Repository.

POC implementation:
- Saves timestamped test reports
- Retrieves individual reports
- Lists report history
- Does not overwrite previous reports

Production should use a durable database,
access controls, and audit retention policies.
"""

import json
import os
import re
import tempfile
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIRECTORY = PROJECT_ROOT / "reports" / "functional_tests"

AGENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
REPORT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class TestReportRepositoryError(Exception):
    pass


class TestReportRepository:

    def __init__(self, report_directory=None):
        self.report_directory = Path(
            report_directory or REPORT_DIRECTORY
        )
        self.report_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    @staticmethod
    def _validate_agent_id(agent_id: str):
        if not AGENT_ID_PATTERN.fullmatch(agent_id):
            raise TestReportRepositoryError(
                "Invalid agent ID."
            )

    @staticmethod
    def _validate_report_id(report_id: str):
        if not REPORT_ID_PATTERN.fullmatch(report_id):
            raise TestReportRepositoryError(
                "Invalid report ID."
            )

    def save_report(
        self,
        report: dict[str, Any],
    ) -> dict[str, Any]:

        if not isinstance(report, dict):
            raise TestReportRepositoryError(
                "Report must be a dictionary."
            )

        agent_id = report.get("agent_id")

        if not isinstance(agent_id, str):
            raise TestReportRepositoryError(
                "Report must contain agent_id."
            )

        self._validate_agent_id(agent_id)

        report_id = uuid.uuid4().hex
        created_at = datetime.now(
            timezone.utc
        ).isoformat()

        saved_report = {
            **report,
            "report_id": report_id,
            "created_at": created_at,
        }

        agent_directory = (
            self.report_directory / agent_id
        )
        agent_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        target = agent_directory / f"{report_id}.json"

        # Write to a temporary file first to avoid
        # leaving partially written JSON reports.
        fd, temporary_path = tempfile.mkstemp(
            prefix=".report_",
            suffix=".tmp",
            dir=agent_directory,
        )

        try:
            with os.fdopen(
                fd,
                "w",
                encoding="utf-8"
            ) as handle:
                json.dump(
                    saved_report,
                    handle,
                    indent=2,
                    default=str,
                )

            os.replace(
                temporary_path,
                target,
            )

        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

        return saved_report

    def get_report(
        self,
        agent_id: str,
        report_id: str,
    ) -> dict[str, Any] | None:

        self._validate_agent_id(agent_id)
        self._validate_report_id(report_id)

        path = (
            self.report_directory
            / agent_id
            / f"{report_id}.json"
        )

        if not path.is_file():
            return None

        with path.open(
            "r",
            encoding="utf-8"
        ) as handle:
            return json.load(handle)

    def list_reports(
        self,
        agent_id: str,
    ) -> list[dict[str, Any]]:

        self._validate_agent_id(agent_id)

        agent_directory = (
            self.report_directory / agent_id
        )

        if not agent_directory.is_dir():
            return []

        reports = []

        for path in agent_directory.glob("*.json"):
            with path.open(
                "r",
                encoding="utf-8"
            ) as handle:
                reports.append(json.load(handle))

        reports.sort(
            key=lambda item: item.get(
                "created_at", ""
            ),
            reverse=True,
        )

        return reports


def save_functional_test_report(
    report: dict[str, Any],
) -> dict[str, Any]:

    repository = TestReportRepository()
    return repository.save_report(report)
