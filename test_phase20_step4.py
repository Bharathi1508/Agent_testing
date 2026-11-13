"""HEAAP Phase 20.4 - Read-only discovery tests."""

from unittest.mock import patch, Mock

from app.services.databricks_readonly_discovery import (
    DatabricksReadOnlyDiscoveryProvider,
)

from app.services.databricks_endpoint_inspector import (
    inspect_databricks_endpoints,
)


def main():
    print("HEAAP PHASE 20.4 - DATABRICKS DISCOVERY")
    print("=" * 55)

    provider = DatabricksReadOnlyDiscoveryProvider(
        host="https://test.cloud.databricks.com",
        token="synthetic-test-token",
        allowed_hosts=["test.cloud.databricks.com"],
    )

    response = Mock()
    response.json.return_value = {
        "endpoints": [
            {"name": "sql-agent-endpoint"},
            {"name": "fraud-agent-endpoint"},
        ]
    }

    response.raise_for_status.return_value = None

    with patch(
        "app.services.databricks_readonly_discovery.requests.get",
        return_value=response,
    ) as mock_get:

        endpoints = provider.discover()

        mock_get.assert_called_once()

        args, kwargs = mock_get.call_args

        assert args[0].endswith(
            "/api/2.0/serving-endpoints"
        )

        assert kwargs["allow_redirects"] is False

    print("Read-only API adapter: PASS")

    candidates = inspect_databricks_endpoints(endpoints)

    assert len(candidates) == 2

    print("Two endpoint candidates identified: PASS")

    assert all(
        item["declared_capabilities"] == []
        for item in candidates
    )

    print("Unknown capabilities not invented: PASS")

    assert all(
        item["execution_authorized"] is False
        for item in candidates
    )

    print("Unauthorized execution prevented: PASS")

    try:
        DatabricksReadOnlyDiscoveryProvider(
            host="https://untrusted.example.com",
            token="synthetic-test-token",
            allowed_hosts=["test.cloud.databricks.com"],
        )

    except PermissionError:
        print("Untrusted workspace blocked: PASS")

    else:
        raise AssertionError("Host allowlist bypassed")

    print()
    print("Live API invoked: False")
    print("Agent endpoint invoked: False")
    print("PHASE 20.4: ALL OFFLINE CHECKS PASSED")


if __name__ == "__main__":
    main()
