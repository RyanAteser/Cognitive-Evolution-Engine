"""Provider-backed multi-trace generation and targeted cognitive correction.

The workflow is deliberately provider-neutral. It asks a configured provider for
independent structured attempts, decodes them against an explicit evidence allowlist,
and performs at most one bounded repair pass. It never treats model agreement as truth.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Protocol

from cee.core.error_correction import (
    CognitiveErrorCorrector,
    CorrectionReport,
    ReasoningTrace,
    Claim,
)
from cee.core.schemas import Candidate, Task
from cee.models.base import ModelProvider


class TraceProvider(Protocol):
    """Minimal generation contract used by the workflow."""
    def generate(self, candidate: Candidate, task: Task): ...


@dataclass(frozen=True)
class CorrectionRun:
    """Immutable record of the original traces, repair trace, and final decode."""
    initial_traces: tuple[ReasoningTrace, ...]
    repair_trace: ReasoningTrace | None
    report: CorrectionReport
    generation_calls: int
    provider_usage: tuple[dict, ...]
    latency_seconds: float


_STRATEGIES = (
    ("independent-solver", "Solve independently. Do not assume another agent's answer."),
    ("skeptical-reviewer", "Try to falsify likely answers. Check assumptions and edge cases."),
    ("evidence-auditor", "Prioritize source-grounded claims; mark unsupported claims explicitly."),
    ("constraint-checker", "Translate the task into constraints and verify each one."),
)


def _extract_json(text: str) -> dict:
    """Parse a JSON object, tolerating a single fenced JSON block."""
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.S)
    if fenced:
        candidate = fenced.group(1)
    else:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("provider response did not contain a JSON object")
        candidate = candidate[start:end + 1]
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("provider response must be a JSON object")
    return value


def parse_reasoning_trace(agent_id: str, response_text: str) -> ReasoningTrace:
    """Convert a provider response into a validated, typed trace."""
    payload = _extract_json(response_text)
    answer = payload.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("trace JSON must contain a non-empty string 'answer'")
    raw_claims = payload.get("claims", [])
    if not isinstance(raw_claims, list):
        raise ValueError("'claims' must be a list")
    claims = []
    for item in raw_claims:
        if not isinstance(item, dict):
            raise ValueError("each claim must be a JSON object")
        claims.append(Claim(
            key=str(item["key"]),
            value=str(item["value"]),
            evidence_ids=tuple(str(x) for x in item.get("evidence_ids", [])),
        ))
    evidence = payload.get("evidence_ids", [])
    errors = payload.get("declared_errors", [])
    if not isinstance(evidence, list) or not isinstance(errors, list):
        raise ValueError("evidence_ids and declared_errors must be lists")
    return ReasoningTrace(
        agent_id=agent_id,
        answer=answer.strip(),
        claims=tuple(claims),
        evidence_ids=tuple(str(x) for x in evidence),
        confidence=float(payload.get("confidence", 0.5)),
        declared_errors=tuple(str(x) for x in errors),
    )


class CognitiveCorrectionWorkflow:
    """Generate diverse traces, decode, and optionally perform one repair pass."""

    def __init__(
        self,
        provider: ModelProvider,
        corrector: CognitiveErrorCorrector | None = None,
        model_name: str = "gemini-2.5-flash",
        max_agents: int = 4,
    ) -> None:
        if max_agents < 2 or max_agents > len(_STRATEGIES):
            raise ValueError("max_agents must be between 2 and 4")
        self.provider = provider
        self.corrector = corrector or CognitiveErrorCorrector()
        self.model_name = model_name
        self.max_agents = max_agents

    def run(
        self,
        task: Task,
        available_evidence_ids: set[str] | None = None,
        repair: bool = True,
    ) -> CorrectionRun:
        started = time.perf_counter()
        traces = []
        provider_usage = []
        for agent_id, instruction in _STRATEGIES[:self.max_agents]:
            candidate = Candidate(
                system_prompt=(
                    "You are one independent reasoning path in a reliability experiment. "
                    "Return only a JSON object with keys: answer (string), claims "
                    "([{key,value,evidence_ids}]), evidence_ids (list), confidence (0..1), "
                    "declared_errors (list). Cite only evidence identifiers provided in "
                    "the task. Never invent identifiers.
Strategy: " + instruction
                ),
                reasoning_strategy=agent_id,
                temperature=0.15 if agent_id == "evidence-auditor" else 0.35,
                max_output_tokens=1400,
            )
            response = self.provider.generate(candidate, task)
            provider_usage.append({
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "estimated_cost": response.estimated_cost,
                "cost_instrumented": False,
            })
            traces.append(parse_reasoning_trace(agent_id, response.text))

        initial = tuple(traces)
        report = self.corrector.decode(initial, available_evidence_ids)
        repair_trace = None
        calls = len(initial)
        if repair and report.syndromes:
            repair_prompt = (
                "A verifier found disagreements in the following independent attempts. "
                "Re-evaluate only the disputed claims, check the original task and allowed "
                "evidence, and do not force consensus. If evidence is insufficient, say so. "
                "Return the same strict JSON schema: answer, claims, evidence_ids, "
                "confidence, declared_errors.

TASK:
" + task.prompt +
                "\n\nATTEMPTS:\n" +
                json.dumps([{
                    "agent_id": t.agent_id,
                    "answer": t.answer,
                    "claims": [{"key": c.key, "value": c.value,
                                "evidence_ids": list(c.evidence_ids)} for c in t.claims],
                    "evidence_ids": list(t.evidence_ids),
                } for t in initial], ensure_ascii=False) +
                "\n\nDETECTED SYNDROMES:\n" +
                json.dumps([s.__dict__ for s in report.syndromes], ensure_ascii=False)
            )
            response = self.provider.generate(
                Candidate(
                    system_prompt=(
                        "You are a targeted repair verifier. Do not merely vote. "
                        "Return only the required JSON object."
                    ),
                    reasoning_strategy="targeted-repair",
                    temperature=0.1,
                    max_output_tokens=1400,
                ),
                Task(task.task_id + "-repair", task.domain, repair_prompt, task.metadata),
            )
            provider_usage.append({
                "model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "estimated_cost": response.estimated_cost,
                "cost_instrumented": False,
            })
            repair_trace = parse_reasoning_trace("targeted-repair", response.text)
            calls += 1
            report = self.corrector.decode(
                initial + (repair_trace,), available_evidence_ids
            )
        return CorrectionRun(
            initial, repair_trace, report, calls, tuple(provider_usage),
            time.perf_counter() - started,
        )
