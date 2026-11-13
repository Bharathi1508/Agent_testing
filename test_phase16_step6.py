import json

from app.services.automatic_assurance_orchestrator import (
    run_automatic_assurance,
)
from app.services.agent_governance_service import (
    assess_agent_governance,
)

agent_id = "sql_agent_001"

assurance = run_automatic_assurance(agent_id)

governance = assess_agent_governance(
    agent_id,
    assurance,
)

print("\nHEAAP PHASE 16.6 GOVERNANCE RESULT")
print("=" * 55)
print(json.dumps(governance, indent=4))

assert governance["production_approved"] is False
assert governance["activation_performed"] is False

print("\nVerified: No production approval or activation.")
