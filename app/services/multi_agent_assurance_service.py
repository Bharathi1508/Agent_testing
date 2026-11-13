"""HEAAP Phase 18.7: explicitly approved multi-agent assurance."""

from app.registry.agent_registry import get_registered_agent
from app.services.unified_adversarial_runner import run_unified_tests
from app.services.unified_evidence_normalizer import (
    normalize_assurance_report,
)
from app.services.phase18_assurance_audit import (
    record_assurance_evidence,
    verify_saved_evidence,
)


ALLOWED_AGENT_MODES = {
    "sql_agent_real_001": "langgraph_real_sql",
}


def run_multi_agent_assurance(
    agent_id,
    tests,
    execution_mode,
    *,
    approved_run=False,
):
    if approved_run is not True:
        raise PermissionError("Explicit test-run approval is required")

    expected_mode = ALLOWED_AGENT_MODES.get(agent_id)

    if expected_mode != execution_mode:
        raise ValueError("Agent and execution mode are not allowlisted")

    agent = get_registered_agent(agent_id)

    if agent is None:
        raise ValueError("Agent is not registered")

    if agent.status != "inactive":
        raise PermissionError("Agent must remain inactive")

    if not isinstance(tests, list) or not tests:
        raise ValueError("Tests must be a nonempty list")

    report = run_unified_tests(
        agent_id=agent_id,
        tests=tests,
        execution_mode=execution_mode,
        approved_run=True,
    )

    evidence = normalize_assurance_report(report)

    audit = record_assurance_evidence(evidence)

    verification = verify_saved_evidence(evidence["evidence_id"])

    if verification["verified"] is not True:
        raise RuntimeError("Saved evidence verification failed")

    return {
        "report": report,
        "evidence": evidence,
        "audit": audit,
        "verification": verification,
    }
