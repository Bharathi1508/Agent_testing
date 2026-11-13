
"""
HEAAP - Adversarial Execution Debugger

Purpose:
    Identify the underlying exception raised
    during an adversarial test.

This script does not change production code.
"""

from app.services.dynamic_supervisor_service import (
    execute_supervisor_request,
)


def main():

    try:
        result = execute_supervisor_request(
            capability="check_column",
            payload={
                "action": "check_column",
                "table_name": "sample_table"
            },
            preferred_agent_id="metadata_agent_001"
        )

        print("Response:", result)

    except Exception as exc:

        print("\nEXCEPTION CHAIN")
        print("-" * 50)

        current = exc
        visited = set()

        while current is not None:

            if id(current) in visited:
                break

            visited.add(id(current))

            print(
                "Exception Type:",
                type(current).__name__
            )

            print(
                "Exception Message:",
                str(current)
            )

            print("-" * 50)

            current = (
                current.__cause__
                or (
                    current.__context__
                    if not current.__suppress_context__
                    else None
                )
            )


if __name__ == "__main__":
    main()
