
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()

HOST = os.environ["DATABRICKS_SERVER_HOSTNAME"]
TOKEN = os.environ["DATABRICKS_TOKEN"]

HOST = HOST.removeprefix("https://").rstrip("/")


def execute_databricks_agent(
    endpoint_name: str,
    question: str
):
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*",
        endpoint_name
    ):
        raise ValueError("Invalid endpoint name")

    # Endpoint names must also be approved
    # in the server-side configuration.
    allowed = {
        value.strip()
        for value in os.getenv(
            "HEAAP_ALLOWED_ENDPOINTS", ""
        ).split(",")
        if value.strip()
    }

    if endpoint_name not in allowed:
        raise ValueError(
            "Endpoint is not approved for execution"
        )

    url = (
        f"https://{HOST}/serving-endpoints/"
        f"{endpoint_name}/invocations"
    )

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ]
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
