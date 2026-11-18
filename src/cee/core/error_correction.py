"""Quantum-inspired classical error detection and correction for reasoning traces."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Claim:
    """A normalized proposition and references to supporting task evidence."""
    key: str
    value: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key.strip() or not self.value.strip():
            raise ValueError("claim key and value must be non-empty")


@dataclass(frozen=True)
class ReasoningTrace:
    """One independently generated attempt at solving a task."""
    agent_id: str
    answer: str
    claims: tuple[Claim, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    confidence: float = 0.5
    declared_errors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class Syndrome:
    """An observable inconsistency or reliability warning."""
    code: str
    severity: str
    agent_ids: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class CorrectionReport:
    """Decoded result and diagnostics required to audit the decision."""
    answer: str | None
    selected_agent: str | None
    syndromes: tuple[Syndrome, ...]
    agent_scores: dict[str, float]
    agreement: float
    corrected: bool
    abstained: bool
    rationale: str


@dataclass
class CognitiveErrorCorrector:
    """Detect disagreement and decode only when evidence supports a choice.

    Agreement is a diagnostic, not proof. Multiple agents can share the same
    blind spot or source error. Scores are heuristics, not probabilities.
    """
    minimum_score: float = 0.25
    minimum_margin: float = 0.15
    consensus_bonus: float = 0.10

    def __post_init__(self) -> None:
        for name in ("minimum_score", "minimum_margin", "consensus_bonus"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")

    def detect(self, traces: Iterable[ReasoningTrace]) -> tuple[Syndrome, ...]:
        """Return deterministic disagreement, contradiction, and error signals."""
        items = tuple(traces)
        if not items:
            raise ValueError("at least one reasoning trace is required")
        syndromes: list[Syndrome] = []
        answer_groups: dict[str, list[str]] = defaultdict(list)
        claim_values: dict[str, dict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for trace in items:
            answer_groups[self._normalize(trace.answer)].append(trace.agent_id)
            for claim in trace.claims:
                claim_values[claim.key][claim.value].append(trace.agent_id)
            if trace.declared_errors:
                syndromes.append(Syndrome(
                    "DECLARED_ERROR", "high", (trace.agent_id,),
                    "; ".join(trace.declared_errors),
                ))
        if len(answer_groups) > 1:
            syndromes.append(Syndrome(
                "ANSWER_DIVERGENCE", "medium", tuple(t.agent_id for t in items),
                f"{len(answer_groups)} distinct normalized answers were produced.",
            ))
        for key, values in claim_values.items():
            if len(values) > 1:
                involved = tuple(sorted({a for agents in values.values() for a in agents}))
                detail = f"Claim {key!r} has conflicting values: " + ", ".join(sorted(values))
                syndromes.append(Syndrome(
                    "CLAIM_CONTRADICTION", "high", involved, detail,
                ))
        return tuple(syndromes)

    def decode(
        self,
        traces: Iterable[ReasoningTrace],
        available_evidence_ids: set[str] | None = None,
    ) -> CorrectionReport:
        """Select a defensible answer or abstain.

        When available_evidence_ids is supplied, references outside that set
        do not count. Callers should pass the task's actual source identifiers.
        """
        items = tuple(traces)
        if not items:
            raise ValueError("at least one reasoning trace is required")
        syndromes = self.detect(items)
        scores: dict[str, float] = {}
        answer_groups: dict[str, list[ReasoningTrace]] = defaultdict(list)
        for trace in items:
            answer_groups[self._normalize(trace.answer)].append(trace)
            trace_evidence = set(trace.evidence_ids)
            claim_evidence = {
                ref for claim in trace.claims for ref in claim.evidence_ids
            }
            all_evidence = trace_evidence | claim_evidence
            if available_evidence_ids is not None:
                all_evidence.intersection_update(available_evidence_ids)
            supported = 0
            for claim in trace.claims:
                refs = set(claim.evidence_ids)
                if available_evidence_ids is not None:
                    refs.intersection_update(available_evidence_ids)
                supported += bool(refs)
            support_ratio = (
                supported / len(trace.claims) if trace.claims
                else (1.0 if trace_evidence else 0.0)
            )
            evidence_count = len(all_evidence)
            error_penalty = min(0.6, 0.25 * len(trace.declared_errors))
            score = 0.55 * support_ratio + 0.25 * min(1.0, evidence_count / 2)
            score += 0.20 * trace.confidence
            scores[trace.agent_id] = max(0.0, min(1.0, score - error_penalty))
        for group in answer_groups.values():
            if len(group) > 1:
                bonus = self.consensus_bonus * (len(group) - 1) / len(items)
                for trace in group:
                    scores[trace.agent_id] = min(1.0, scores[trace.agent_id] + bonus)
        ranked = sorted(items, key=lambda t: scores[t.agent_id], reverse=True)
        winner = ranked[0]
        runner_up = scores[ranked[1].agent_id] if len(ranked) > 1 else 0.0
        margin = scores[winner.agent_id] - runner_up
        agreement = len(answer_groups[self._normalize(winner.answer)]) / len(items)
        if scores[winner.agent_id] < self.minimum_score:
            return CorrectionReport(
                None, None, syndromes, scores, agreement, False, True,
                "No reasoning path met the minimum evidence/reliability score.",
            )
        if len(ranked) > 1 and margin < self.minimum_margin:
            return CorrectionReport(
                None, None, syndromes, scores, agreement, False, True,
                "Top candidates were too close; abstaining is safer than forced consensus.",
            )
        return CorrectionReport(
            winner.answer, winner.agent_id, syndromes, scores, agreement,
            bool(syndromes), False,
            "Selected the highest-scoring trace using evidence support, declared errors, "
            "and a limited agreement bonus.",
        )

    @staticmethod
    def _normalize(answer: str) -> str:
        return " ".join(answer.casefold().split())
