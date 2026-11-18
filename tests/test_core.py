import pytest

from cee.core.evolution import EvolutionEngine
from cee.core.schemas import Candidate, Evaluation
from cee.storage import ExperimentStore


def test_fingerprint_stable():
    assert Candidate("Be accurate").fingerprint == Candidate("Be accurate").fingerprint


def test_sampling_validation():
    with pytest.raises(ValueError):
        Candidate("x", temperature=3)


def test_evolution():
    seed = Candidate("Solve carefully")
    engine = EvolutionEngine(seed=3)
    population = engine.initial_population(seed, 6)
    best, score, history = engine.evolve(
        population,
        lambda candidate: 1.0 if "evidence" in candidate.system_prompt else 0.2,
        generations=3,
        population_size=6,
    )
    assert isinstance(best, Candidate)
    assert 0 <= score <= 1
    assert len(history) == 3


def test_store(tmp_path):
    store = ExperimentStore(tmp_path / "test.db")
    candidate = Candidate("Be careful")
    evaluation = Evaluation(candidate.fingerprint, "task-1", 0.5, "sample")
    store.save_evaluation(candidate, evaluation)
    assert store.counts() == {"candidates": 1, "evaluations": 1}
