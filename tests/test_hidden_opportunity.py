import json

import pytest

from cee.experiments.hidden_opportunity import build_task, load_cases


def test_load_cases_keeps_split_and_never_requires_answer_key(tmp_path):
    dataset = tmp_path / "cases.jsonl"
    rows = [
        {"case_id": "s1", "domain": "shopify", "split": "validation",
         "task": "find an opportunity", "packet": [{"id": "x", "text": "fact"}]},
        {"case_id": "s2", "domain": "shopify", "split": "validation",
         "task": "find another opportunity", "packet": [{"id": "z", "text": "another fact"}]},
        {"case_id": "q1", "domain": "quant", "split": "test",
         "task": "find a hypothesis", "packet": [{"id": "y", "text": "fact"}]},
    ]
    dataset.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    selected = load_cases(dataset, "validation")
    assert [x["case_id"] for x in selected] == ["s1", "s2"]


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


def test_committed_dataset_is_balanced_and_answer_key_is_complete():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    dataset = root / "benchmarks" / "datasets" / "hidden_opportunity_v1.jsonl"
    answer_key = root / "benchmarks" / "answer_keys" / "hidden_opportunity_v1.json"
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    key = json.loads(answer_key.read_text(encoding="utf-8"))
    assert len(rows) == 12
    assert len(key["cases"]) == 12
    assert {row["case_id"] for row in rows} == set(key["cases"])
    for domain in ("shopify", "quant"):
        for split in ("train", "validation", "test"):
            assert sum(row["domain"] == domain and row["split"] == split for row in rows) == 2
