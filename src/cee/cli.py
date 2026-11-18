"""CEE command line."""
import argparse
import os
import time
from pathlib import Path

from cee.adapters.general import GeneralResearchAdapter
from cee.core.evolution import EvolutionEngine
from cee.core.schemas import Candidate, Evaluation
from cee.models.gemini import GeminiProvider
from cee.storage import ExperimentStore
from cee.experiments.hidden_opportunity import run_experiment


def run_demo() -> int:
    seed = Candidate("Solve accurately. Separate evidence from assumptions.")
    engine = EvolutionEngine(seed=11)
    population = engine.initial_population(seed, 8)

    # Synthetic fitness verifies optimizer wiring only; it is not a model benchmark.
    def fitness(candidate: Candidate) -> float:
        prompt = candidate.system_prompt.lower()
        score = (
            0.35
            + 0.15 * ("assumptions" in prompt)
            + 0.15 * ("counterexample" in prompt)
            + 0.15 * ("evidence" in prompt)
            + 0.10 * (candidate.reasoning_strategy != "direct")
            + 0.10 * (candidate.temperature <= 0.4)
        )
        return min(score, 1.0)

    best, score, history = engine.evolve(
        population, fitness, generations=5, population_size=8
    )
    print("CEE offline demo (synthetic fitness; not evidence of task performance)")
    print(f"fitness={score:.3f}; strategy={best.reasoning_strategy}; temperature={best.temperature}")
    print(f"generations={len(history)}")
    return 0


def run_task(domain: str, prompt: str) -> int:
    if domain != "general":
        raise SystemExit(
            "Live Gemini runner currently supports general tasks only; "
            "domain-specific evaluators are required."
        )
    task = GeneralResearchAdapter().build_task(prompt)
    provider = GeminiProvider()
    candidate = Candidate(
        "Be accurate. Separate evidence from inference and state uncertainty."
    )
    started = time.perf_counter()
    response = provider.generate(candidate, task)
    latency = time.perf_counter() - started
    store = ExperimentStore(os.getenv("CEE_DATABASE", "cee_experiments.sqlite3"))
    # Do not fabricate a score: general tasks require a rubric or verified answer key.
    evaluation = Evaluation(
        candidate.fingerprint,
        task.task_id,
        0.0,
        response.text,
        latency_seconds=latency,
        metrics={"requires_external_rubric": 1.0},
    )
    store.save_evaluation(candidate, evaluation)
    print(response.text)
    print(f"\nmodel={response.model}; latency={latency:.2f}s; score=unscored (no rubric)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="cee")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("demo")
    subparsers.add_parser("status")
    experiment_parser = subparsers.add_parser("experiment-001")
    experiment_parser.add_argument("--split", choices=("train", "validation", "test"), default="validation")
    experiment_parser.add_argument("--arms", default="A,B,C,D,E")
    experiment_parser.add_argument("--dataset", default="benchmarks/datasets/hidden_opportunity_v1.jsonl")
    experiment_parser.add_argument("--output", default="research/experiment_001/validation_run.json")
    experiment_parser.add_argument("--repeats", type=int, default=1)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument(
        "--domain", default="general", choices=("general", "shopify", "finance")
    )
    run_parser.add_argument("--task", required=True)
    args = parser.parse_args()

    if args.command == "demo":
        raise SystemExit(run_demo())
    if args.command == "status":
        database = os.getenv("CEE_DATABASE", "cee_experiments.sqlite3")
        print(ExperimentStore(database).counts())
        return
    if args.command == "run":
        raise SystemExit(run_task(args.domain, args.task))
    if args.command == "experiment-001":
        arms = tuple(dict.fromkeys(x.strip().upper() for x in args.arms.split(",") if x.strip()))
        if not arms or any(x not in {"A", "B", "C", "D", "E"} for x in arms):
            raise SystemExit("--arms must contain one or more of A,B,C,D,E")
        run_experiment(Path(args.dataset), Path(args.output), args.split, arms, repeats=args.repeats)
        return


if __name__ == "__main__":
    main()
