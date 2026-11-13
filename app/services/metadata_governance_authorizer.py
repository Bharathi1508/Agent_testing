"""
HEAAP Governance Authorizer

Uses the existing persistent registry, whose get_agent()
method revalidates onboarding approval on each retrieval.
"""


class MetadataGovernanceAuthorizer:

    def __init__(self, registry):
        if not callable(getattr(registry, "get_agent", None)):
            raise ValueError("Valid registry required")

        self.registry = registry

    def authorize(self, agent_id):

        if not isinstance(agent_id, str) or not agent_id.strip():
            return False

        try:
            record = self.registry.get_agent(agent_id)

            if not isinstance(record, dict):
                return False

            manifest = record.get("manifest")
            review = record.get("review")

            if not isinstance(manifest, dict):
                return False

            if not isinstance(review, dict):
                return False

            if manifest.get("agent_id") != agent_id:
                return False

            if review.get("agent", {}).get("agent_id") != agent_id:
                return False

            # The registry must have already revalidated
            # the approval record and manifest.
            return True

        except Exception:
            return False
