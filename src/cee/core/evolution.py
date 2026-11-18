"""Transparent genetic search over candidate model configurations."""
from __future__ import annotations
import random
from dataclasses import replace
from typing import Callable, Iterable
from cee.core.schemas import Candidate

Fitness = Callable[[Candidate], float]


class EvolutionEngine:
    """Initial baseline optimizer; fitness must be supplied by a task-grounded evaluator."""
    STRATEGIES = ("direct", "plan_then_answer", "verify_then_answer", "counterexample_first")

    def __init__(self, seed: int = 7, mutation_rate: float = 0.35) -> None:
        if not 0.0 <= mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be between 0 and 1")
        self.rng = random.Random(seed)
        self.mutation_rate = mutation_rate

    def mutate(self, candidate: Candidate) -> Candidate:
        variants = (
            "State assumptions explicitly and distinguish evidence from inference.",
            "Generate alternatives, then select using stated evaluation criteria.",
            "Check the answer for counterexamples and unsupported claims.",
            "Prefer testable conclusions; state uncertainty when evidence is insufficient.",
            "Identify the objective, constraints, and failure conditions before solving.",
        )
        prompt = candidate.system_prompt
        strategy = candidate.reasoning_strategy
        temperature = candidate.temperature
        if self.rng.random() < self.mutation_rate:
            prompt += "\n\n" + self.rng.choice(variants)
        if self.rng.random() < self.mutation_rate:
            strategy = self.rng.choice(self.STRATEGIES)
        if self.rng.random() < self.mutation_rate:
            temperature = self.rng.choice((0.0, 0.1, 0.2, 0.4, 0.7, 1.0))
        return replace(candidate, system_prompt=prompt, reasoning_strategy=strategy,
                       temperature=temperature)

    def initial_population(self, seed: Candidate, size: int) -> list[Candidate]:
        if size < 2:
            raise ValueError("population size must be at least 2")
        population = [seed]
        while len(population) < size:
            population.append(self.mutate(seed))
        return self._deduplicate(population)

    def evolve(self, population: Iterable[Candidate], fitness: Fitness,
               generations: int = 3, population_size: int | None = None):
        current = self._deduplicate(list(population))
        if not current:
            raise ValueError("population cannot be empty")
        target = population_size or len(current)
        history = []
        for generation in range(generations):
            ranked = sorted(((fitness(c), c) for c in current), key=lambda x: x[0], reverse=True)
            history.append({"generation": float(generation), "best_fitness": ranked[0][0],
                            "mean_fitness": sum(x[0] for x in ranked) / len(ranked)})
            parents = [c for _, c in ranked[:max(1, len(ranked) // 2)]]
            current = parents[:]
            while len(current) < target:
                current.append(self.mutate(self.rng.choice(parents)))
            current = self._deduplicate(current)
            while len(current) < target:
                current.append(self.mutate(self.rng.choice(parents)))
        ranked = sorted(((fitness(c), c) for c in current), key=lambda x: x[0], reverse=True)
        return ranked[0][1], ranked[0][0], history

    @staticmethod
    def _deduplicate(candidates: list[Candidate]) -> list[Candidate]:
        return list({c.fingerprint: c for c in candidates}.values())
