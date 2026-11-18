"""CEE command line."""
import argparse, os, time
from cee.adapters.general import GeneralResearchAdapter
from cee.core.evolution import EvolutionEngine
from cee.core.schemas import Candidate, Evaluation
from cee.models.gemini import GeminiProvider
from cee.storage import ExperimentStore

def run_demo():
    seed = Candidate("Solve accurately. Separate evidence from assumptions.")
    engine = EvolutionEngine(seed=11)
    population = engine.initial_population(seed, 8)
    # Synthetic fitness only verifies optimizer wiring; it is not a model benchmark.
    def fitness(c):
        p = c.system_prompt.lower()
        return min(.35 + .15 * ("assumptions" in p) + .15 * ("counterexample" in p)
                   + .15 * ("evidence" in p) + .1 * (c.reasoning_strategy != "direct")
                   + .1 * (c.temperature <= .4), 1.0)
    best, score, history = engine.evolve(population, fitness, generations=5, population_size=8)
    print("CEE offline demo (synthetic fitness; not evidence of task performance)")
    print(f"fitness={score:.3f}; strategy={best.reasoning_strategy}; temperature={best.temperature}")
    print(f"generations={len(history)}")
    return 0

def run_task(domain, prompt):
    if domain != "general":
        raise SystemExit("Live Gemini runner currently supports general tasks only; domain-specific evaluators are required.")
    task = GeneralResearchAdapter().build_task(prompt)
    provider = GeminiProvider()
    candidate = Candidate("Be accurate. Separate evidence from inference and state uncertainty.")
    started = time.perf_counter()
    response = provider.generate(candidate, task)
    latency = time.perf_counter() - started
    store = ExperimentStore(os.getenv("CEE_DATABASE", "cee_experiments.sqlite3"))
    # No score is fabricated: general tasks require a rubric or verified answer key.
    store.save_evaluation(candidate, Evaluation(candidate.fingerprint, task.task_id, 0.0,
        response.text, latency_seconds=latency, metrics={"requires_external_rubric": 1.0}))
    print(response.text)
    print(f"\nmodel={response.model}; latency={latency:.2f}s; score=unscored (no rubric)")
    return 0

def main():
    parser = argparse.ArgumentParser(prog="cee")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo")
    sub.add_parser("status")
    run = sub.add_parser("run")
    run.add_argument("--domain", default="general", choices=("general", "shopify", "finance"))
    run.add_argument("--task", required=True)
    args = parser.parse_args()
    if args.command == "demo": raise SystemExit(run_demo())
    if args.command == "status":
        print(ExperimentStore(os.getenv("CEE_DATABASE", "cee_experiments.sqlite3")).counts())
        return
    if args.command == "run": raise SystemExit(run_task(args.domain, args.task))

if __name__ == "__main__": main()
