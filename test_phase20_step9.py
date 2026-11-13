"""HEAAP Phase 20.9 - Dashboard API tests."""

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.phase20_dashboard_app import app
from app.api.routes import assurance_dashboard
from app.services.assurance_dashboard_service import (
    AssuranceDashboardService,
)


def main():
    print("HEAAP PHASE 20.9 - DASHBOARD API")
    print("=" * 55)

    with tempfile.TemporaryDirectory() as temp_dir:

        fixture = {
            "phase": "20.7",
            "report_id": "test_report_001",
            "created_at": "2026-11-06T00:00:00+00:00",
            "overall_verdict": "PASS",
            "agents": [
                {
                    "agent_id": "sql_agent_001",
                    "verdict": "PASS",
                },
                {
                    "agent_id": "metadata_agent_001",
                    "verdict": "PASS",
                },
                {
                    "agent_id": "fraud_agent_001",
                    "verdict": "FAIL",
                },
            ],
        }

        path = Path(temp_dir) / "test_report_001.json"
        path.write_text(
            json.dumps(fixture),
            encoding="utf-8",
        )

        original_service = assurance_dashboard.service

        assurance_dashboard.service = (
            AssuranceDashboardService(temp_dir)
        )

        try:
            client = TestClient(app)

            response = client.get("/health")
            assert response.status_code == 200
            print("Health endpoint: PASS")

            response = client.get("/api/assurance/summary")
            assert response.status_code == 200

            summary = response.json()

            assert summary["total_reports"] == 1
            assert summary["unique_agents"] == 3
            assert summary["passed"] == 2
            assert summary["failed"] == 1

            print("Assurance summary endpoint: PASS")

            response = client.get("/api/assurance/reports")
            assert response.status_code == 200
            assert len(response.json()["reports"]) == 1

            print("Report listing endpoint: PASS")

            response = client.get(
                "/api/assurance/reports/test_report_001"
            )

            assert response.status_code == 200
            assert response.json()["report_id"] == "test_report_001"

            print("Report detail endpoint: PASS")

            response = client.get(
                "/api/assurance/agents/sql_agent_001/history"
            )

            assert response.status_code == 200
            assert response.json()["total_evaluations"] == 1

            print("Agent history endpoint: PASS")

            response = client.get(
                "/api/assurance/reports/missing_report"
            )

            assert response.status_code == 404

            print("Missing report handling: PASS")

            response = client.get(
                "/api/assurance/reports/invalid.id"
            )

            assert response.status_code == 400

            print("Invalid report ID handling: PASS")

        finally:
            assurance_dashboard.service = original_service

    print()
    print("Live Databricks endpoint invoked: False")
    print("Production approval granted: False")
    print("PHASE 20.9: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
