
"""
HEAAP - Hybrid Enterprise Agent Assurance Platform

Module:
    Adversarial Response Adapter

Purpose:
    Convert agent execution responses and exceptions
    into a standardized structure for adversarial
    test evaluation.

Responsibilities:
    1. Normalize successful agent responses.
    2. Inspect supervisor and agent exception chains.
    3. Identify trusted input-validation exceptions.
    4. Preserve structured validation error codes.
    5. Return unknown for unverified failures.

Inputs:
    - Agent execution response
    - Exception raised during agent execution

Outputs:
    {
        "status": "rejected | success | unknown",
        "error_code": "INVALID_INPUT | INVALID_ACTION | None",
        "source": "...",
        "observation": "..."
    }

Security:
    Never treat arbitrary exceptions as proof
    that an adversarial test passed.
"""

from typing import Any

from app.services.agent_executor import (
    AgentInputValidationError,
)


class AdversarialResponseAdapter:
    """
    Normalizes agent execution results into
    a consistent response structure.
    """

    ALLOWED_VALIDATION_CODES = {
        "INVALID_INPUT",
        "INVALID_ACTION",
    }

    @staticmethod
    def from_success(response: Any) -> dict[str, Any]:
        """
        Normalize an agent response.

        A successful execution must not be
        mistaken for an expected rejection.
        """

        if not isinstance(response, dict):
            return {
                "status": "unknown",
                "error_code": None,
                "source": "supervisor",
                "observation": (
                    "Execution returned an unexpected "
                    "response structure."
                ),
            }

        if response.get("status") == "success":
            return {
                "status": "success",
                "error_code": None,
                "source": "supervisor",
                "observation": (
                    "Agent execution completed successfully."
                ),
            }

        return {
            "status": "unknown",
            "error_code": None,
            "source": "supervisor",
            "observation": (
                "Execution returned a response "
                "requiring further verification."
            ),
        }

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
    ) -> dict[str, Any]:
        """
        Inspect the complete exception chain.

        A verified rejection is returned only
        when the exception originates from
        the trusted HEAAP input validator.
        """

        exception_chain = []

        current = exc
        visited = set()

        while current is not None:

            if id(current) in visited:
                break

            visited.add(id(current))

            exception_chain.append({
                "exception_type": type(current).__name__,
                "message": str(current),
            })

            if isinstance(
                current,
                AgentInputValidationError,
            ):

                error_code = getattr(
                    current,
                    "error_code",
                    None,
                )

                if error_code in cls.ALLOWED_VALIDATION_CODES:

                    return {
                        "status": "rejected",
                        "error_code": error_code,
                        "source": "agent_input_validator",
                        "observation": str(current),
                        "exception_chain": exception_chain,
                    }

            if current.__cause__ is not None:
                current = current.__cause__

            elif not current.__suppress_context__:
                current = current.__context__

            else:
                current = None

        return {
            "status": "unknown",
            "error_code": None,
            "source": "exception",
            "observation": (
                "Agent execution failed, but no "
                "verified input-validation rejection "
                "was found."
            ),
            "exception_chain": exception_chain,
        }


def adapt_adversarial_success(
    response: Any,
) -> dict[str, Any]:
    """
    Public function used by the
    adversarial test runner.
    """

    return AdversarialResponseAdapter.from_success(
        response
    )


def adapt_adversarial_exception(
    exc: Exception,
) -> dict[str, Any]:
    """
    Public function used by the
    adversarial test runner.
    """

    return AdversarialResponseAdapter.from_exception(
        exc
    )
