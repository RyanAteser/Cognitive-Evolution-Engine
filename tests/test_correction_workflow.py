import json

import pytest

from cee.core.correction_workflow import (
    CognitiveCorrectionWorkflow,
    parse_reasoning_trace,
)
from cee.core.error_correction import CognitiveErrorCorrector
from cee.core.schemas import Task
from cee.models.base import ModelResponse


def test_parse_structured_trace_and_evidence():
    trace = parse_reasoning_trace("agent-a", json.dumps({
        "answer": "42",
        "claims": [{"key": "result", "value": "42", "evidence_ids": ["s1"]}],
        "evidence_ids": ["s1"],
        "confidence": 0.8,
        "declared_errors": [],
    }))
    assert trace.agent_id == "agent-a"
    assert trace.claims[0].evidence_ids == ("s1",)


def test_parser_rejects_missing_answer():
    with pytest.raises(ValueError):
        parse_reasoning_trace("agent-a", '{"claims": []}')


class FakeProvider:
    def __init__(self):
        self.calls = []

    def generate(self, candidate, task):
        self.calls.append((candidate, task))
        if candidate.reasoning_strategy == "targeted-repair":
            payload = {
                "answer": "The supported answer is 42.",
                "claims": [{"key": "result", "value": "42", "evidence_ids": ["s1"]}],
                "evidence_ids": ["s1"],
                "confidence": 0.9,
                "declared_errors": [],
            }
        else:
            idx = len(self.calls)
            value = "42" if idx in (1, 3) else "17"
            payload = {
                "answer": f"The answer is {value}.",
                "claims": [{"key": "result", "value": value,
                            "evidence_ids": ["s1"] if value == "42" else []}],
                "evidence_ids": ["s1"] if value == "42" else [],
                "confidence": 0.8,
                "declared_errors": [],
            }
        return ModelResponse(json.dumps(payload), "fake-model")


def test_workflow_generates_independent_paths_and_one_repair():
    provider = FakeProvider()
    workflow = CognitiveCorrectionWorkflow(
        provider, CognitiveErrorCorrector(minimum_margin=0.01), max_agents=2
    )
    task = Task("t1", "general", "What is the result?", {})
    result = workflow.run(task, {"s1"}, repair=True)
    assert len(result.initial_traces) == 2
    assert result.repair_trace is not None
    assert result.generation_calls == 3
    assert len(result.provider_usage) == 3
    assert result.latency_seconds >= 0
    assert result.report.answer == "The supported answer is 42."


def test_workflow_can_disable_repair():
    provider = FakeProvider()
    workflow = CognitiveCorrectionWorkflow(provider, max_agents=2)
    task = Task("t2", "general", "Answer.", {})
    result = workflow.run(task, {"s1"}, repair=False)
    assert result.repair_trace is None
    assert result.generation_calls == 2
    assert len(result.provider_usage) == 2
    assert len(provider.calls) == 2
