"""Phase 19.4 - Persistent external assurance integration."""

from app.services.external_agent_assurance_orchestrator import (
    ExternalAgentAssuranceOrchestrator,
)
from app.services.persistent_external_agent_registry import (
    PersistentExternalAgentRegistry,
)
from app.services.persistent_external_assurance_audit import (
    PersistentExternalAssuranceAudit,
)


class Phase19PersistentAssuranceService:

    def __init__(self, registry=None, audit=None):
        self.registry = registry or PersistentExternalAgentRegistry()
        self.audit = audit or PersistentExternalAssuranceAudit()

    def register_agent(self, manifest, review_file):
        return self.registry.register_agent(manifest, review_file)

    def run_assurance(
        self,
        agent_id,
        capability,
        tests,
        *,
        approved_run=False,
    ):
        if approved_run is not True:
            raise PermissionError(
                "Explicit mock test-run approval required"
            )

        record = self.registry.get_agent(agent_id)

        orchestrator = ExternalAgentAssuranceOrchestrator()

        orchestrator.register_reviewed_agent(
            record["manifest"],
            record["review"],
        )

        report = orchestrator.run_assurance(
            capability,
            tests,
            agent_id=agent_id,
            approved_run=True,
        )

        evidence_id = self.audit.save_report(report)

        return {
            "report": report,
            "evidence_id": evidence_id,
            "audit_verified": self.audit.verify_report(evidence_id),
        }
