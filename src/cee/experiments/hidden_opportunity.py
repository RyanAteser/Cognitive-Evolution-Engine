"""Executable, answer-key-blind runner for CEE Experiment #001.

The runner generates and freezes model outputs only. It deliberately does not load
the evaluator answer key or assign semantic scores. Human scoring is performed later
from a separately randomized blind-review sheet.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cee.core.correction_workflow import CognitiveCorrectionWorkflow
from cee.core.error_correction import CognitiveErrorCorrector
from cee.core.schemas import Candidate, Task
from cee.models.gemini import GeminiProvider

DATASET_VERSION = "hidden_opportunity_v1"
AGENT_ROLES = (
    ("opportunity-scout", "Find non-obvious but evidence-supported opportunities."),
    ("skeptic", "Try to falsify candidate opportunities; identify counter-evidence."),
    ("evidence-auditor", "Check that each inference is supported by packet evidence IDs."),
    ("constraint-checker", "Check domain constraints, feasibility, and unsafe leaps."),
)
ARMS = ("A", "B", "C", "D", "E")


def load_cases(path: Path, split: str) -> list[dict[str, Any]]:
    """Load solver-visible JSONL cases. Never reads the evaluator answer key."""
    cases = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        required = {"case_id", "domain", "split", "task", "packet"}
        if not required.issubset(case):
            raise ValueError(f"line {line_number}: missing required case fields")
        if case["case_id"] in seen:
            raise ValueError(f"duplicate case_id: {case['case_id']}")
        seen.add(case["case_id"])
        if case["split"] == split:
            cases.append(case)
    if len(cases) < 2:
        raise ValueError(f"split {split!r} must contain at least two cases")
    return cases


def build_task(case: dict[str, Any]) -> Task:
    packet = json.dumps(case["packet"], ensure_ascii=False, indent=2)
    prompt = (
        "RESEARCH TASK
"
        f"Domain: {case['domain']}
"
        f"{case['task']}

"
        "EVIDENCE PACKET (the IDs below are the only permitted citations):
"
        f"{packet}

"
        "OUTPUT REQUIREMENTS
"
        "Return a structured report with: (1) up to two candidate opportunities; "
        "(2) target customer or market condition; (3) evidence IDs and explicit "
        "inference chain; (4) counter-evidence and alternative explanations; "
        "(5) unknowns; (6) a cheap falsifiable validation experiment; "
        "(7) measurable success/failure criteria; (8) confidence from 0 to 100 "
        "with justification. Distinguish observations, inferences, and recommendations. "
        "Cite only supplied IDs. Do not invent facts. A justified abstention is valid. "
        "Do not recommend live trading, publication, or unapproved store changes."
    )
    return Task(case["case_id"], case["domain"], prompt, {"case_id": case["case_id"]})


def _call(provider: GeminiProvider, task: Task, role: str, instruction: str,
          temperature: float = 0.25) -> dict[str, Any]:
    candidate = Candidate(
        system_prompt=(
            "You are participating in a controlled research benchmark. "
            "Do not assume facts not in the task. Preserve uncertainty. "
            + instruction
        ),
        reasoning_strategy=role,
        temperature=temperature,
        max_output_tokens=1800,
    )
    started = time.perf_counter()
    response = provider.generate(candidate, task)
    return {
        "role": role,
        "text": response.text,
        "model": response.model,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "estimated_cost": response.estimated_cost,
        "latency_seconds": time.perf_counter() - started,
    }


def run_arm(arm: str, provider: GeminiProvider, task: Task,
            available_evidence_ids: set[str]) -> dict[str, Any]:
    if arm == "A":
        calls = [_call(
            provider, task, "single-pass",
            "Solve the research task independently. Return the requested complete report.",
        )]
        return {"final_output": calls[0]["text"], "calls": calls}

    if arm in {"B", "C"}:
        independent = [
            _call(provider, task, role, instruction)
            for role, instruction in AGENT_ROLES
        ]
        if arm == "B":
            synthesis_instruction = (
                "Synthesize the independent analyses into one report. Preserve unresolved "
                "disagreement and do not force consensus. Cite the evidence IDs."
            )
        else:
            synthesis_instruction = (
                "Use a majority-vote approach: identify conclusions supported by the "
                "largest number of independent analyses. Do not treat agreement as proof; "
                "flag disagreement and unsupported claims. Return one report."
            )
        synthesis_task = Task(
            task.task_id + "-synthesis", task.domain,
            task.prompt + "

INDEPENDENT ANALYSES:
" +
            json.dumps([{"role": x["role"], "text": x["text"]} for x in independent],
                       ensure_ascii=False),
            task.metadata,
        )
        synthesis = _call(
            provider, synthesis_task, "synthesizer", synthesis_instruction, 0.15
        )
        return {
            "final_output": synthesis["text"],
            "independent_traces": independent,
            "calls": independent + [synthesis],
        }

    if arm in {"D", "E"}:
        workflow = CognitiveCorrectionWorkflow(
            provider=provider,
            corrector=CognitiveErrorCorrector(),
            model_name=getattr(provider, "model", "gemini"),
            max_agents=4,
        )
        correction = workflow.run(
            task, available_evidence_ids=available_evidence_ids,
            repair=(arm == "E"),
        )
        final_output = correction.report.answer
        if final_output is None:
            final_output = (
                "ABSTAIN: " + correction.report.rationale +
                "
Initial traces:
" +
                "
".join(t.answer for t in correction.initial_traces)
            )
        return {
            "final_output": final_output,
            "initial_traces": [
                {
                    "agent_id": t.agent_id, "answer": t.answer,
                    "claims": [
                        {"key": c.key, "value": c.value,
                         "evidence_ids": list(c.evidence_ids)} for c in t.claims
                    ],
                    "evidence_ids": list(t.evidence_ids),
                    "confidence": t.confidence,
                    "declared_errors": list(t.declared_errors),
                } for t in correction.initial_traces
            ],
            "repair_trace": None if correction.repair_trace is None else {
                "agent_id": correction.repair_trace.agent_id,
                "answer": correction.repair_trace.answer,
                "evidence_ids": list(correction.repair_trace.evidence_ids),
                "confidence": correction.repair_trace.confidence,
            },
            "correction_report": {
                "syndromes": [s.__dict__ for s in correction.report.syndromes],
                "agent_scores": correction.report.agent_scores,
                "agreement": correction.report.agreement,
                "abstained": correction.report.abstained,
                "rationale": correction.report.rationale,
            },
            "calls": [{"role": "cee-workflow", "generation_calls":
                       correction.generation_calls, "provider_usage":
                       list(correction.provider_usage), "latency_seconds":
                       correction.latency_seconds}],
        }
    raise ValueError(f"unknown arm: {arm}")


def run_experiment(dataset: Path, output: Path, split: str,
                   selected_arms: tuple[str, ...], seed: int = 20261118) -> Path:
    cases = load_cases(dataset, split)
    provider = GeminiProvider()
    dataset_hash = hashlib.sha256(dataset.read_bytes()).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    blind_order = list(selected_arms)
    random.Random(seed).shuffle(blind_order)
    blind_labels = {arm: f"blind-{index + 1:02d}"
                    for index, arm in enumerate(blind_order)}
    manifest = {
        "dataset_version": DATASET_VERSION,
        "dataset_sha256": dataset_hash,
        "split": split,
        "model": provider.model,
        "arms": list(selected_arms),
        "blind_labels": blind_labels,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "answer_key_loaded": False,
        "scoring": "human_blind_review_required",
    }
    records = []
    for case in cases:
        task = build_task(case)
        evidence_ids = {item["id"] for item in case["packet"]}
        for arm in selected_arms:
            result = run_arm(arm, provider, task, evidence_ids)
            records.append({
                "case_id": case["case_id"],
                "domain": case["domain"],
                "split": split,
                "blind_label": blind_labels[arm],
                "raw_arm": arm,
                "result": result,
                "dataset_sha256": dataset_hash,
                "model": provider.model,
            })
    # Freeze all outputs in one JSON document. Keep raw_arm in the sealed
    # research archive; blind review export below excludes it and all model traces.
    archive = {"manifest": {k: v for k, v in manifest.items() if k != "blind_labels"},
               "records": records}
    unblind_path = output.with_name(output.stem + "_unblind_key.json")
    unblind_path.write_text(json.dumps({"blind_labels": blind_labels}, indent=2) + "\
",
                            encoding="utf-8")
    output.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "
",
                      encoding="utf-8")
    review_path = output.with_name(output.stem + "_blind_review.csv")
    with review_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "case_id", "domain", "blind_label", "final_output",
            "evidence_grounding_0_25", "novelty_0_15", "reasoning_0_15",
            "counter_evidence_0_15", "testability_0_15",
            "calibration_0_10", "constraints_0_5",
            "unsupported_claims", "critical_failure", "reviewer_notes",
        ])
        writer.writeheader()
        for record in records:
            writer.writerow({
                "case_id": record["case_id"],
                "domain": record["domain"],
                "blind_label": record["blind_label"],
                "final_output": result_text(record["result"]),
            })
    print(f"Frozen raw run: {output}")
    print(f"Blind scoring sheet: {review_path}")
    print("Evaluator answer key was not loaded. Scores require independent human review.")
    return output


def result_text(result: dict[str, Any]) -> str:
    return str(result.get("final_output", ""))


def main() -> None:
    parser = argparse.ArgumentParser(prog="cee-experiment-001")
    parser.add_argument("--split", choices=("train", "validation", "test"),
                        default="validation")
    parser.add_argument("--arms", default="A,B,C,D,E",
                        help="Comma-separated arms: A,B,C,D,E")
    parser.add_argument("--dataset", type=Path, default=Path(
        "benchmarks/datasets/hidden_opportunity_v1.jsonl"))
    parser.add_argument("--output", type=Path, default=Path(
        "research/experiment_001/validation_run.json"))
    parser.add_argument("--seed", type=int, default=20261118)
    args = parser.parse_args()
    arms = tuple(dict.fromkeys(x.strip().upper() for x in args.arms.split(",") if x.strip()))
    if not arms or any(x not in ARMS for x in arms):
        parser.error("--arms must contain one or more of A,B,C,D,E")
    run_experiment(args.dataset, args.output, args.split, arms, args.seed)


if __name__ == "__main__":
    main()
