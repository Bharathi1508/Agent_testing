from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentExecutionRequest:
    agent_id: str
    capability: str
    payload: dict[str, Any]
    test_id: str


@dataclass
class AgentExecutionResult:
    agent_id: str
    capability: str
    test_id: str
    status: str
    response: dict[str, Any] | None
    error_code: str | None
    execution_target: str


class RealAgentAdapter(ABC):

    @abstractmethod
    def execute(
        self,
        request: AgentExecutionRequest,
    ) -> AgentExecutionResult:
        pass
