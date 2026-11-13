
"""
HEAAP - Dynamic Agent Onboarding Service

Responsibilities:
1. Receive a discovered agent manifest.
2. Validate the manifest.
3. Check whether the agent is already registered.
4. Register new agents as inactive.
5. Run assurance tests when available.
6. Require governance approval before activation.

Security:
- Discovery does not grant approval.
- Validation does not grant approval.
- Registration does not activate an agent.
- Existing agent governance state is preserved.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


# --------------------------------------------------
# Dependency adapter types
# --------------------------------------------------

ManifestValidator = Callable[[dict[str, Any]], Any]

RegistryLookup = Callable[[str], Any]

RegistryRegister = Callable[[dict[str, Any]], Any]

AssuranceRunner = Callable[[dict[str, Any]], Any]


# --------------------------------------------------
# Onboarding response model
# --------------------------------------------------

@dataclass
class OnboardingResponse:
    agent_id: str
    success: bool
    status: str
    message: str

    validation_passed: bool = False
    registered: bool = False
    assurance_passed: bool | None = None
    approval_required: bool = True

    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "success": self.success,
            "status": self.status,
            "message": self.message,
            "validation_passed": self.validation_passed,
            "registered": self.registered,
            "assurance_passed": self.assurance_passed,
            "approval_required": self.approval_required,
            "errors": self.errors,
        }


# --------------------------------------------------
# Utility functions
# --------------------------------------------------

def _as_dict(value: Any) -> dict[str, Any]:
    """
    Convert a dictionary or Pydantic model
    into a standard Python dictionary.
    """

    if isinstance(value, dict):
        return value.copy()

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if hasattr(value, "dict"):
        return value.dict()

    raise TypeError(
        "Expected a dictionary or Pydantic model."
    )


async def _invoke(
    function: Callable[..., Any],
    *args: Any,
) -> Any:
    """
    Execute a synchronous or asynchronous function.
    """

    result = function(*args)

    if inspect.isawaitable(result):
        return await result

    return result


# --------------------------------------------------
# Main onboarding service
# --------------------------------------------------

class OnboardingService:
    """
    Coordinates dynamic onboarding of HEAAP agents.

    Existing validator, registry and assurance
    functions are supplied through dependency
    injection.

    This avoids circular imports and allows
    different agent providers to be supported.
    """

    def __init__(
        self,
        validator: ManifestValidator,
        registry_lookup: RegistryLookup,
        registry_register: RegistryRegister,
        assurance_runner: AssuranceRunner | None = None,
    ) -> None:

        self.validator = validator
        self.registry_lookup = registry_lookup
        self.registry_register = registry_register
        self.assurance_runner = assurance_runner

    # ----------------------------------------------
    # Main onboarding workflow
    # ----------------------------------------------

    async def onboard(
        self,
        discovered_agent: dict[str, Any] | Any,
    ) -> dict[str, Any]:

        # Step 1: Convert input into dictionary.
        try:
            manifest = _as_dict(discovered_agent)

        except (TypeError, ValueError) as exc:
            return OnboardingResponse(
                agent_id="unknown",
                success=False,
                status="rejected",
                message="Invalid agent payload.",
                errors=[str(exc)],
            ).to_dict()

        agent_id = str(
            manifest.get("agent_id") or ""
        ).strip()

        if not agent_id:
            return OnboardingResponse(
                agent_id="unknown",
                success=False,
                status="rejected",
                message="Agent ID is required.",
                errors=["Missing agent_id"],
            ).to_dict()

        # ------------------------------------------
        # Step 2: Validate manifest
        # ------------------------------------------

        try:
            validation_result = await _invoke(
                self.validator,
                manifest,
            )

            validation = _as_dict(validation_result)

        except Exception as exc:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="validation_error",
                message="Manifest validation could not run.",
                errors=[str(exc)],
            ).to_dict()

        if validation.get("valid") is not True:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="rejected",
                message="Agent manifest failed validation.",
                errors=[
                    str(error)
                    for error in (
                        validation.get("errors") or []
                    )
                ],
            ).to_dict()

        normalized = validation.get(
            "normalized_manifest"
        )

        if normalized is None:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="validation_error",
                message=(
                    "Validator did not return "
                    "a normalized manifest."
                ),
                validation_passed=True,
                errors=["Missing normalized_manifest"],
            ).to_dict()

        try:
            normalized_manifest = _as_dict(normalized)

        except (TypeError, ValueError) as exc:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="validation_error",
                message="Invalid normalized manifest.",
                validation_passed=True,
                errors=[str(exc)],
            ).to_dict()

        normalized_id = str(
            normalized_manifest.get("agent_id") or ""
        ).strip()

        if normalized_id != agent_id:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="validation_error",
                message=(
                    "Normalized agent ID does not "
                    "match the submitted agent ID."
                ),
                errors=["Agent ID mismatch"],
            ).to_dict()

        # Never activate a newly discovered agent.
        normalized_manifest["status"] = "inactive"
        normalized_manifest["approved"] = False

        normalized_manifest.setdefault(
            "discovered_at",
            datetime.now(timezone.utc).isoformat(),
        )

        # ------------------------------------------
        # Step 3: Check existing registration
        # ------------------------------------------

        try:
            existing_agent = await _invoke(
                self.registry_lookup,
                agent_id,
            )

        except Exception as exc:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="registry_error",
                message="Agent registry lookup failed.",
                validation_passed=True,
                errors=[str(exc)],
            ).to_dict()

        if existing_agent is not None:
            return OnboardingResponse(
                agent_id=agent_id,
                success=True,
                status="already_registered",
                message=(
                    "Agent already exists in the registry. "
                    "Existing approval and activation "
                    "state have not been modified."
                ),
                validation_passed=True,
                registered=True,
            ).to_dict()

        # ------------------------------------------
        # Step 4: Register new agent
        # ------------------------------------------

        try:
            registration_result = await _invoke(
                self.registry_register,
                normalized_manifest,
            )

            if registration_result is False:
                raise RuntimeError(
                    "Registry rejected registration."
                )

        except Exception as exc:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="registration_error",
                message="Agent registration failed.",
                validation_passed=True,
                errors=[str(exc)],
            ).to_dict()

        # ------------------------------------------
        # Step 5: Assurance testing
        # ------------------------------------------

        if self.assurance_runner is None:
            return OnboardingResponse(
                agent_id=agent_id,
                success=True,
                status="pending_assurance",
                message=(
                    "Agent registered as inactive. "
                    "Assurance testing is required."
                ),
                validation_passed=True,
                registered=True,
                assurance_passed=None,
            ).to_dict()

        try:
            assurance_result = await _invoke(
                self.assurance_runner,
                normalized_manifest,
            )

            assurance = _as_dict(assurance_result)

            assurance_passed = (
                assurance.get("passed") is True
            )

        except Exception as exc:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="assurance_error",
                message=(
                    "Agent registered as inactive, "
                    "but assurance testing encountered "
                    "an error."
                ),
                validation_passed=True,
                registered=True,
                assurance_passed=False,
                errors=[str(exc)],
            ).to_dict()

        if not assurance_passed:
            return OnboardingResponse(
                agent_id=agent_id,
                success=False,
                status="assurance_failed",
                message=(
                    "Agent registered as inactive, "
                    "but assurance tests did not pass."
                ),
                validation_passed=True,
                registered=True,
                assurance_passed=False,
            ).to_dict()

        # ------------------------------------------
        # Step 6: Governance approval required
        # ------------------------------------------

        return OnboardingResponse(
            agent_id=agent_id,
            success=True,
            status="pending_approval",
            message=(
                "Agent passed validation and assurance. "
                "Governance approval is required "
                "before activation."
            ),
            validation_passed=True,
            registered=True,
            assurance_passed=True,
        ).to_dict()
