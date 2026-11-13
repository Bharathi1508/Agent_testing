from databricks import sql
from app.config import (
    DATABRICKS_HOST,
    DATABRICKS_HTTP_PATH,
    DATABRICKS_TOKEN,
)


def execute_query(query, parameters=None):
    with sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters or [])

            if cursor.description is None:
                return []

            columns = [c[0] for c in cursor.description]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]