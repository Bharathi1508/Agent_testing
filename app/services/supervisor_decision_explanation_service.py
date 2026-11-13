"""HEAAP Phase 21.7 - Explain recorded supervisor decisions."""

from app.services.assurance_test_details_service import (
    AssuranceTestDetailsService,
)


class SupervisorDecisionExplanationService:

    def __init__(self, evidence_service=None):
        self.evidence_service = (
            evidence_service
            if evidence_service is not None
            else AssuranceTestDetailsService()
        )

    def explain(self, report_id, agent_id):
        result = self.evidence_service.get_agent_tests(
            report_id, agent_id
        )

        if result is None:
            return None

        evidence = result["evidence"]
        verdict = str(result.get("verdict") or "UNKNOWN").upper()

        descriptions = {
            "PASS": (
                "The recorded supervisor verdict is PASS. "
                "This indicates the evaluated checks were reported "
                "as passing in this assurance run."
            ),
            "FAIL": (
                "The recorded supervisor verdict is FAIL. "
                "Inspect the attached evidence to identify "
                "the failed checks and their recorded reasons."
            ),
            "UNSUPPORTED": (
                "The recorded supervisor verdict is UNSUPPORTED. "
                "The evaluation did not establish support for "
                "the requested capability or test contract."
            ),
        }

        explanation = descriptions.get(
            verdict,
            "The recorded verdict is not recognized as PASS, "
            "FAIL, or UNSUPPORTED. Manual investigation is required.",
        )

        requires_review = verdict != "PASS"

        return {
            "report_id": report_id,
            "agent_id": agent_id,
            "created_at": result.get("created_at"),
            "execution_mode": result.get("execution_mode"),
            "recorded_verdict": verdict,
            "explanation": explanation,
            "explanation_type": "deterministic_verdict_interpretation",
            "requires_review_by_verdict": requires_review,
            "evidence": evidence,
            "limitations": [
                "This is an interpretation of a stored verdict, "
                "not a reconstruction of private supervisor reasoning.",
                "A PASS in offline mock testing does not verify "
                "a live agent's capabilities.",
                "Production approval must be verified separately "
                "through the authorized governance workflow.",
            ],
            "governance": {
                "read_only": True,
                "approval_performed": False,
                "execution_performed": False,
                "production_approval_verified": False,
            },
        }
