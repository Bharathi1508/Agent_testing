"""
HEAAP Phase 22.14
Real Metadata Agent Test Adapter.

Requires:
- An explicitly authorized HTTP adapter
- Agent-specific request payloads
- A supported response contract

Authorization and registry approval must be
enforced by the invoking orchestration layer.
"""

from app.services.metadata_response_normalizer import (
    MetadataResponseNormalizer,
)


class RealMetadataTestAdapter:

    def __init__(self, http_adapter):
        self.http_adapter = http_adapter
        self.normalizer = MetadataResponseNormalizer()

    def execute(self, test_case):

        if not isinstance(test_case, dict):
            raise ValueError("Invalid test case")

        raw_response = self.http_adapter.execute(
            test_case
        )

        return self.normalizer.normalize(
            test_case,
            raw_response,
        )
