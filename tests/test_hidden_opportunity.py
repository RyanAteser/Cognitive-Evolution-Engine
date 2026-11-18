import json

import pytest

from cee.experiments.hidden_opportunity import build_task, load_cases


def test_load_cases_keeps_split_and_never_requires_answer_key(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    rows = [
        {"case_id": "s1", "domain": "shopify", "split": "validation",
         "task": "find an opportunity", "packet": [{"id": "x", "text": "fact"}]},
        {"case_id": "q1", "domain": "quant", "split": "test",
         "task": "find a hypothesis", "packet": [{"id": "y", "text": "fact"}]},
    ]
    dataset.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    selected = load_cases(dataset, "validation")
    assert [x["case_id"] for x in selected] == ["s1"]


def test_load_cases_rejects_duplicate_ids(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    row = {"case_id": "same", "domain": "shopify", "split": "test",
           "task": "task", "packet": [{"id": "x"}]}
    dataset.write_text(json.dumps(row) + "\n" + json.dumps(row), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(dataset, "test")


def test_build_task_includes_only_solver_packet():
    case = {"case_id": "shopify-1", "domain": "shopify", "task": "Find a need.",
            "packet": [{"id": "P1", "text": "Repeated customer complaint."}]}
    task = build_task(case)
    assert "P1" in task.prompt
    assert "Repeated customer complaint" in task.prompt
    assert "answer_key" not in task.prompt
