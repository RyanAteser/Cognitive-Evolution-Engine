# CEE Benchmark Protocol

## Why a benchmark is mandatory

CEE is intended to improve workflows, not merely generate more elaborate prompts or more agent calls. Every proposed change must be compared with a frozen baseline on the same tasks, under the same resource limits. A system that scores better only on tasks used to tune it has not demonstrated general improvement.

## Dataset splits

Every benchmark case belongs to an explicit split:

- **Train:** optimization may inspect scores and use these cases to change prompts or workflows.
- **Validation:** choose between candidate versions and tune policy thresholds.
- **Test (holdout):** locked until a candidate is frozen. Run only for promotion decisions. Do not feed test errors back into the same optimization cycle; doing so contaminates the holdout.

Keep task IDs, expected answers/rubrics, source snapshots, dataset version, model version, prompts, and scoring code versioned. Do not change a test set silently. Maintain a separate fresh holdout when a test set becomes exposed.

## Paired experiment

1. Freeze the baseline, candidate, task set, model version, tools, evidence, and budget.
2. Run both systems on the exact same task IDs. Repeat runs when generation is stochastic.
3. Score with deterministic answer keys where possible, otherwise a blinded domain rubric or verified outcome. Exact match is only a starter metric; it is not a general reasoning evaluator.
4. Record per-task score, latency, token usage/cost, exceptions, abstentions, and tool failures.
5. Compute paired per-task quality differences and a bootstrap confidence interval. Keep the raw per-task observations so aggregate scores can be audited.
6. Promote only when the held-out quality gain clears a predeclared threshold, the lower confidence bound exceeds that threshold, and cost, latency, and failure-rate guardrails pass.

The included `BenchmarkRunner` is a minimal deterministic harness. It supports repeated paired runs, a pluggable scorer, cost/latency/error summaries, a paired bootstrap interval, and a conservative promotion gate. Its default exact-match scorer is a smoke-test baseline, not a substitute for domain evaluation.

## Required metrics

| Metric | What it catches |
|---|---|
| Task quality / accuracy | Whether answers actually improve |
| Paired quality delta + confidence interval | Whether the gain is consistent, not just aggregate noise |
| Error / failure rate | Provider failures and broken workflows |
| Abstention coverage and selective accuracy | Whether refusing uncertain answers is calibrated |
| Evidence precision / citation entailment | Whether cited sources really support claims |
| Correction precision / false correction rate | Whether the repair step fixes faults or introduces new ones |
| Robustness under controlled faults | Whether reliability survives perturbations |
| Mean and p95 latency | Whether quality costs too much time |
| Cost per task / token usage | Whether quality costs too much money |

Do not collapse everything into one score too early. Report the quality-cost-latency-reliability frontier and make trade-offs explicit.

## Cognitive error-correction ablations

Use the same task/fault set to compare:
1. Single-pass baseline.
2. Multi-agent generation with majority vote only.
3. Multi-agent generation plus syndrome detection.
4. Syndrome detection plus evidence-aware decoding.
5. Full system with targeted repair.
6. Full system with repair disabled (to isolate repair's contribution).

For each, run clean and fault-injected examples. Faults should include wrong numeric values, contradictory claims, unsupported evidence IDs, missing constraints, malformed structured output, stale source excerpts, and shared misleading evidence. Keep clean controls so the benchmark measures false alarms as well as detection.

## Domain-specific suites

- **General reasoning:** answerable questions with reference answers, multi-hop evidence tasks, arithmetic/code tests, and adversarial counterexamples.
- **Shopify:** sandbox-only tasks with exact expected state changes; include product edits, inventory constraints, pricing rules, policy compliance, and recovery from tool errors. Never benchmark by making unapproved production changes.
- **Quant / prediction markets:** time-ordered, point-in-time datasets; walk-forward splits; realistic fees, spreads, slippage, latency, and no look-ahead. Compare to simple baselines and require out-of-sample net performance. A backtest win is not proof of live edge.

## Promotion policy

A candidate is not promoted merely because it has higher average score. The improvement must be repeatable, statistically credible under the chosen test, within resource budgets, and free of a worse execution failure rate. Human review is required for high-impact domain suites. If the evidence is inconclusive, keep the incumbent.

## Current limitations

- The included harness does not ship with a validated general reasoning dataset.
- Its default exact-match metric is intentionally simple.
- Bootstrap intervals are descriptive and depend on representative, independent task sampling; they do not repair dataset leakage or poor labels.
- Cost is only as accurate as the provider's returned cost field. Gemini provider currently reports token counts but does not calculate price.
- P95 latency, token totals, semantic citation verification, abstention calibration, and correction-specific metrics are planned extensions.


## Included smoke dataset

`benchmarks/datasets/general_smoke_v1.jsonl` is a tiny, versioned fixture with explicit
train/validation/test assignments. It exists to exercise dataset parsing, split discipline,
and end-to-end benchmark wiring with deterministic arithmetic examples. It is **synthetic
infrastructure test data**, not a representative reasoning benchmark and not evidence that
CEE or any correction strategy is better. Do not use its test split to tune a candidate; once
used for development, treat it as an exposed smoke test and create a fresh holdout for any
real promotion claim.
