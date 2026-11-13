from datetime import datetime, timezone
import hashlib
import json
import os
import re

from databricks import sql


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class TrustedReferenceBuilder:

    def __init__(self, catalog, schema):
        for name in (catalog, schema):
            if not IDENTIFIER.fullmatch(name):
                raise ValueError("Invalid catalog or schema")

        self.catalog = catalog
        self.schema = schema

    def build_table_reference(self, table_name):
        if not IDENTIFIER.fullmatch(table_name):
            raise ValueError("Invalid table name")

        hostname = os.environ["DATABRICKS_HOST"]
        http_path = os.environ["DATABRICKS_HTTP_PATH"]
        token = os.environ["DATABRICKS_TOKEN"]

        hostname = (
            hostname.replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
        )

        query = f"""
        SELECT
            column_name,
            data_type,
            ordinal_position
        FROM `{self.catalog}`.information_schema.columns
        WHERE table_catalog = ?
          AND table_schema = ?
          AND table_name = ?
        ORDER BY ordinal_position
        """

        with sql.connect(
            server_hostname=hostname,
            http_path=http_path,
            access_token=token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    query,
                    [
                        self.catalog,
                        self.schema,
                        table_name,
                    ],
                )

                rows = cursor.fetchall()

        columns = [
            {
                "column_name": row[0],
                "data_type": row[1],
                "ordinal_position": row[2],
            }
            for row in rows
        ]

        if not columns:
            raise LookupError(
                "No metadata returned. Verify table "
                "existence and Unity Catalog permissions."
            )

        canonical = json.dumps(
            {
                "catalog": self.catalog,
                "schema": self.schema,
                "table": table_name,
                "columns": columns,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        fingerprint = hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

        return {
            "reference_type": "unity_catalog_schema",
            "source": "databricks_information_schema",
            "catalog": self.catalog,
            "schema": self.schema,
            "table": table_name,
            "retrieved_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "columns": columns,
            "column_count": len(columns),
            "fingerprint": fingerprint,
            "reference_verified": True,
        }
