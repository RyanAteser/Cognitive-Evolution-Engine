from cee.core.evolution import EvolutionEngine
from cee.core.schemas import Candidate, Evaluation
from cee.storage import ExperimentStore

def test_fingerprint_stable():
    assert Candidate("Be accurate").fingerprint == Candidate("Be accurate").fingerprint

def test_sampling_validation():
    try: Candidate("x", temperature=3)
    except ValueError: pass
    else: raise AssertionError("invalid temperature accepted")

def test_evolution():
    seed = Candidate("Solve carefully")
    engine = EvolutionEngine(seed=3)
    population = engine.initial_population(seed, 6)
    best, score, history = engine.evolve(population,
        lambda c: 1.0 if "evidence" in c.system_prompt else .2, generations=3, population_size=6)
    assert isinstance(best, Candidate) and 0 <= score <= 1 and len(history) == 3

def test_store(tmp_path):
    store = ExperimentStore(tmp_path / "test.db")
    c = Candidate("Be careful")
    store.save_evaluation(c, Evaluation(c.fingerprint, "task-1", .5, "sample"))
    assert store.counts() == {"candidates": 1, "evaluations": 1}
