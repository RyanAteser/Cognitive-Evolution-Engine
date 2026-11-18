from dataclasses import dataclass
from typing import Protocol
from cee.core.schemas import Candidate, Task

@dataclass
class ModelResponse:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float = 0.0

class ModelProvider(Protocol):
    def generate(self, candidate: Candidate, task: Task) -> ModelResponse: ...
