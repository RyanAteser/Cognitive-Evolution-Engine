from dataclasses import dataclass, field
from typing import Any, Protocol
from cee.core.schemas import Task

@dataclass
class DomainDefinition:
    name: str
    description: str
    success_metrics: list[str]
    constraints: list[str] = field(default_factory=list)

class DomainAdapter(Protocol):
    definition: DomainDefinition
    def build_task(self, prompt: str, metadata: dict[str, Any] | None = None) -> Task: ...
    def score(self, task: Task, output: str) -> tuple[float, dict[str, float]]: ...
