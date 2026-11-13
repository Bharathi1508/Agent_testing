
from app.services.agent_executor import (
    AgentInputValidationError,
    validate_metadata_payload,
)

payload = {
    "action": "check_column",
    "table_name": "customers",
}

try:
    validate_metadata_payload(payload)

    print("FAILED: Invalid payload was accepted.")

except AgentInputValidationError as exc:
    print("PASSED: Invalid payload was rejected.")
    print("Error Code:", exc.error_code)
    print("Message:", str(exc))
