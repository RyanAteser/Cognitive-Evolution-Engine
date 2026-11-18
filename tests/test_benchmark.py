from cee.core.benchmark import (
    BenchmarkCase,
    BenchmarkRunner,
    PromotionPolicy,
)
from cee.core.schemas import Task
from cee.models.base import ModelResponse


def cases(split="test"):
    return [
        BenchmarkCase(Task("a", "general", "Q1", {}), "right", split),
        BenchmarkCase(Task("b", "general", "Q2", {}), "right", split),
        BenchmarkCase(Task("c", "general", "Q3", {}), "wrong", split),
    ]


def test_paired_benchmark_detects_quality_improvement_and_promotes():
    policy = PromotionPolicy(
        minimum_quality_gain=0.05,
        maximum_cost_ratio=2.0,
        maximum_latency_ratio=10.0,
        bootstrap_samples=200,
    )
    runner = BenchmarkRunner(policy=policy)
    report = runner.compare(
        cases(),
        "baseline", lambda task: "wrong",
        "candidate", lambda task: "right" if task.task_id != "c" else "wrong",
        repeats=2,
    )
    assert report.mean_quality_gain == 2 / 3
    assert report.confidence_interval[0] > 0.05
    assert report.promoted


def test_validation_results_cannot_promote():
    runner = BenchmarkRunner(policy=PromotionPolicy(bootstrap_samples=100))
    report = runner.compare(
        cases("validation"), "baseline", lambda task: "wrong",
        "candidate", lambda task: "right",
        split="validation",
    )
    assert not report.promoted
    assert any("held-out" in reason for reason in report.reasons)


def test_cost_and_errors_are_reported_and_gate_promotion():
    runner = BenchmarkRunner(policy=PromotionPolicy(bootstrap_samples=100))
    report = runner.compare(
        cases(), "baseline", lambda task: ModelResponse("wrong", "baseline", estimated_cost=0.001),
        "candidate", lambda task: (_ for _ in ()).throw(RuntimeError("provider down")),
    )
    assert report.candidate.error_rate == 1.0
    assert not report.promoted
    assert report.candidate.mean_cost == 0.0


def test_rejects_duplicate_ids_and_too_small_split():
    runner = BenchmarkRunner()
    duplicate = [
        BenchmarkCase(Task("x", "g", "q", {}), "a"),
        BenchmarkCase(Task("x", "g", "q2", {}), "a"),
    ]
    import pytest
    with pytest.raises(ValueError, match="unique"):
        runner.compare(duplicate, "b", lambda task: "a", "c", lambda task: "a")
    with pytest.raises(ValueError, match="two cases"):
        runner.compare(cases()[:1], "b", lambda task: "a", "c", lambda task: "a")
