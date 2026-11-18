"""Typed experiment definitions."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
import hashlib
import json


@dataclass(frozen=True)
class Candidate:
    """Candidate configuration: instructions and inference-time settings."""
    system_prompt: str
    reasoning_strategy: str = "direct"
    temperature: float = 0.2
    top_p: float = 1.0
    max_output_tokens: int = 1024
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0 and 2")
        if not 0.0 < self.top_p <= 1.0:
            raise ValueError("top_p must be in (0, 1]")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Task:
    task_id: str
    domain: str
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Evaluation:
    candidate_id: str
    task_id: str
    score: float
    output: str
    latency_seconds: float = 0.0
    estimated_cost: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")
