"""Paired, repeatable benchmark runner and conservative promotion gate.

Benchmark cases must be authored with explicit splits. The runner never creates
or changes a split, and promotion is permitted only on the held-out test split.
"""
from __future__ import annotations

import random
import re
import statistics
import time
from dataclasses import dataclass
from typing import Callable, Iterable

from cee.core.schemas import Task
from cee.models.base import ModelResponse


Scorer = Callable[[str, str], float]
System = Callable[[Task], str | ModelResponse]


@dataclass(frozen=True)
class BenchmarkCase:
    task: Task
    expected_output: str
    split: str = "test"

    def __post_init__(self) -> None:
        if self.split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        if not self.task.task_id.strip():
            raise ValueError("benchmark task_id must be non-empty")


@dataclass(frozen=True)
class PromotionPolicy:
    minimum_quality_gain: float = 0.01
    maximum_cost_ratio: float = 1.25
    maximum_latency_ratio: float = 1.50
    bootstrap_samples: int = 2000
    confidence_level: float = 0.95
    random_seed: int = 7

    def __post_init__(self) -> None:
        if self.minimum_quality_gain < 0:
            raise ValueError("minimum_quality_gain cannot be negative")
        if self.maximum_cost_ratio <= 0 or self.maximum_latency_ratio <= 0:
            raise ValueError("cost and latency ratios must be positive")
        if self.bootstrap_samples < 100:
            raise ValueError("bootstrap_samples must be at least 100")
        if not 0.5 < self.confidence_level < 1:
            raise ValueError("confidence_level must be between 0.5 and 1")


@dataclass(frozen=True)
class SystemMetrics:
    quality: float
    mean_latency_seconds: float
    mean_cost: float
    error_rate: float
    observations: int


@dataclass(frozen=True)
class BenchmarkReport:
    split: str
    baseline_name: str
    candidate_name: str
    baseline: SystemMetrics
    candidate: SystemMetrics
    mean_quality_gain: float
    confidence_interval: tuple[float, float]
    promoted: bool
    reasons: tuple[str, ...]


@dataclass
class _Observation:
    score: float
    latency: float
    cost: float
    failed: bool


def exact_match_scorer(output: str, expected: str) -> float:
    """Simple deterministic baseline scorer; domains should supply better rubrics."""
    def normalize(value: str) -> str:
        return " ".join(re.sub(r"\\s+", " ", value).casefold().split())

    return float(normalize(output) == normalize(expected))


def _response_parts(value: str | ModelResponse) -> tuple[str, float]:
    if isinstance(value, ModelResponse):
        return value.text, max(0.0, value.estimated_cost)
    if isinstance(value, str):
        return value, 0.0
    raise TypeError("benchmark systems must return str or ModelResponse")


def _mean_metrics(items: list[_Observation]) -> SystemMetrics:
    return SystemMetrics(
        quality=statistics.fmean(item.score for item in items),
        mean_latency_seconds=statistics.fmean(item.latency for item in items),
        mean_cost=statistics.fmean(item.cost for item in items),
        error_rate=sum(item.failed for item in items) / len(items),
        observations=len(items),
    )


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _paired_bootstrap_interval(
    differences: list[float], policy: PromotionPolicy
) -> tuple[float, float]:
    rng = random.Random(policy.random_seed)
    samples = []
    for _ in range(policy.bootstrap_samples):
        draw = [rng.choice(differences) for _ in differences]
        samples.append(statistics.fmean(draw))
    alpha = 1.0 - policy.confidence_level
    return (
        _percentile(samples, alpha / 2),
        _percentile(samples, 1 - alpha / 2),
    )


class BenchmarkRunner:
    """Evaluate baseline and candidate on identical tasks and repeated runs."""

    def __init__(self, scorer: Scorer = exact_match_scorer,
                 policy: PromotionPolicy | None = None) -> None:
        self.scorer = scorer
        self.policy = policy or PromotionPolicy()

    def compare(
        self,
        cases: Iterable[BenchmarkCase],
        baseline_name: str,
        baseline_system: System,
        candidate_name: str,
        candidate_system: System,
        split: str = "test",
        repeats: int = 1,
    ) -> BenchmarkReport:
        if split not in {"train", "validation", "test"}:
            raise ValueError("split must be train, validation, or test")
        if repeats < 1:
            raise ValueError("repeats must be at least 1")
        selected = [case for case in cases if case.split == split]
        ids = [case.task.task_id for case in selected]
        if len(ids) != len(set(ids)):
            raise ValueError("benchmark task IDs must be unique within a split")
        if len(selected) < 2:
            raise ValueError("at least two cases are required for paired evaluation")

        baseline_by_case: dict[str, list[_Observation]] = {}
        candidate_by_case: dict[str, list[_Observation]] = {}
        for case in selected:
            baseline_by_case[case.task.task_id] = []
            candidate_by_case[case.task.task_id] = []
            for _ in range(repeats):
                for system, bucket in (
                    (baseline_system, baseline_by_case[case.task.task_id]),
                    (candidate_system, candidate_by_case[case.task.task_id]),
                ):
                    started = time.perf_counter()
                    try:
                        output, cost = _response_parts(system(case.task))
                        elapsed = time.perf_counter() - started
                        score = float(self.scorer(output, case.expected_output))
                        if not 0.0 <= score <= 1.0:
                            raise ValueError("scorer must return a value between 0 and 1")
                        bucket.append(_Observation(score, elapsed, cost, False))
                    except Exception:
                        elapsed = time.perf_counter() - started
                        bucket.append(_Observation(0.0, elapsed, 0.0, True))

        baseline_items = [item for values in baseline_by_case.values() for item in values]
        candidate_items = [item for values in candidate_by_case.values() for item in values]
        baseline_metrics = _mean_metrics(baseline_items)
        candidate_metrics = _mean_metrics(candidate_items)
        paired_differences = [
            statistics.fmean(item.score for item in candidate_by_case[case_id])
            - statistics.fmean(item.score for item in baseline_by_case[case_id])
            for case_id in ids
        ]
        gain = statistics.fmean(paired_differences)
        interval = _paired_bootstrap_interval(paired_differences, self.policy)

        reasons = []
        if split != "test":
            reasons.append("Promotion is blocked: results were not measured on held-out test data.")
        if interval[0] <= self.policy.minimum_quality_gain:
            reasons.append(
                "Quality gain did not clear the required minimum with the lower confidence bound."
            )
        if baseline_metrics.mean_cost == 0:
            if candidate_metrics.mean_cost > 0:
                reasons.append("Candidate incurs cost while baseline cost is zero.")
        elif candidate_metrics.mean_cost / baseline_metrics.mean_cost > self.policy.maximum_cost_ratio:
            reasons.append("Candidate exceeds the allowed mean cost ratio.")
        if baseline_metrics.mean_latency_seconds > 0 and (
            candidate_metrics.mean_latency_seconds / baseline_metrics.mean_latency_seconds
            > self.policy.maximum_latency_ratio
        ):
            reasons.append("Candidate exceeds the allowed mean latency ratio.")
        if candidate_metrics.error_rate > baseline_metrics.error_rate:
            reasons.append("Candidate has a higher execution error rate than baseline.")
        return BenchmarkReport(
            split, baseline_name, candidate_name, baseline_metrics, candidate_metrics,
            gain, interval, not reasons, tuple(reasons),
        )
