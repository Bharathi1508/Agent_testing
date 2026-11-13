from app.services.multi_agent_contract_supervisor import (
    MultiAgentContractSupervisor,
)

from app.services.persistent_external_assurance_audit import (
    PersistentExternalAssuranceAudit,
)


class MultiAgentPersistentAuditService:

    def __init__(self, supervisor, audit=None):

        if not isinstance(
            supervisor,
            MultiAgentContractSupervisor,
        ):
            raise TypeError(
                "MultiAgentContractSupervisor required"
            )

        self.supervisor = supervisor

        self.audit = (
            audit
            if audit is not None
            else PersistentExternalAssuranceAudit()
        )

    def run_and_audit(
        self,
        manifests,
        *,
        mock_run_authorized=False,
    ):

        if mock_run_authorized is not True:
            raise PermissionError(
                "Explicit mock-run authorization required"
            )

        report = self.supervisor.run(
            manifests,
            mock_run_authorized=True,
        )

        evidence = []

        for agent_report in report["agents"]:

            evidence_id = self.audit.save_report(
                agent_report
            )

            if self.audit.verify_report(evidence_id) is not True:
                raise RuntimeError(
                    "Agent audit verification failed"
                )

            evidence.append({
                "agent_id": agent_report["agent_id"],
                "evidence_id": evidence_id,
                "verified": True,
            })

        # The existing audit requires a top-level agent_id.
        # Use a separate identity for supervisor-level evidence.
        consolidated_report = {
            **report,
            "agent_id": "heaap_supervisor",
            "report_type": "multi_agent_consolidated",
        }

        consolidated_evidence_id = self.audit.save_report(
            consolidated_report
        )

        if self.audit.verify_report(
            consolidated_evidence_id
        ) is not True:
            raise RuntimeError(
                "Consolidated audit verification failed"
            )

        return {
            "phase": "20.8",
            "report": report,
            "agent_evidence": evidence,
            "consolidated_evidence_id": consolidated_evidence_id,
            "audit_verified": True,
            "live_endpoint_invoked": False,
            "production_approved": False,
        }

    def get_evidence(self, evidence_id):
        return self.audit.get_report(evidence_id)

    def verify_evidence(self, evidence_id):
        return self.audit.verify_report(evidence_id)

    def list_agent_history(self, agent_id):
        return self.audit.list_reports(agent_id=agent_id)
