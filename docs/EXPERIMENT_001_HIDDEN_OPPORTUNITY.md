# CEE Experiment #001: Hidden Opportunity Discovery

## Objective

Measure whether the Cognitive-Evolution-Engine (CEE) improves a model's ability to discover *non-obvious, evidence-supported opportunities* from incomplete, noisy, and sometimes contradictory evidence.

The benchmark is cross-domain. Shopify cases represent commercial/product opportunities; quantitative-research cases represent candidate market-behavior hypotheses. The cognitive task and output schema are shared. Domain-specific scoring checks differ.

This is a research benchmark, not an instruction to publish content, alter a Shopify store, place trades, or claim a profitable strategy.

## Preregistered hypothesis

H1: CEE's full correction workflow will improve evidence-grounded opportunity quality over a single-pass Gemini baseline on the held-out test set.

H2: CEE will reduce unsupported claims and missed contradictions, without exceeding the predeclared cost and latency budgets.

A null or negative result is valid. Do not tune prompts, thresholds, scoring rules, or model settings against the test split.

## Benchmark structure

- Dataset: `benchmarks/datasets/hidden_opportunity_v1.jsonl`
- Evaluator-only key: `benchmarks/answer_keys/hidden_opportunity_v1.json`
- Split manifest: included in each case as `split`; train/validation/test are balanced across domains.
- All cases are synthetic and self-contained. They test the pipeline and reasoning behavior, not real-world market performance.
- Do not provide the answer key to any solver, reviewer, or repair agent.
- The initial dataset is a smoke benchmark (12 cases), not sufficient for strong statistical claims. Expand to at least 60 cases (30/domain) before treating results as generalizable.

## Task presented to every system

Given a research packet, identify up to two plausible opportunities that are *not explicitly stated as recommendations* in the packet. For each opportunity provide:

1. concise opportunity statement;
2. target user/customer or market condition;
3. evidence IDs and the exact inference chain connecting them;
4. counter-evidence and alternative explanations;
5. what remains unknown;
6. a cheap, falsifiable validation experiment;
7. measurable success and failure criteria;
8. confidence (0-100) and why;
9. a clear abstention if evidence is insufficient.

Do not invent missing facts. Separate observations, inferences, and recommendations. A valid answer may be "no defensible opportunity found."

## Fixed experimental arms

Run every case on the same model version, provider settings, temperature, tool access, source packet, and output budget.

| Arm | Configuration | Purpose |
|---|---|---|
| A | Gemini single-pass | Baseline |
| B | Independent multi-agent analysis; no voting/correction | Isolate decomposition |
| C | Independent agents + majority vote | Isolate consensus |
| D | CEE syndrome detection + evidence-aware decoding; repair off | Isolate correction |
| E | Full CEE with one bounded targeted repair | Primary candidate |

If the current code cannot yet run an arm exactly as described, record it as unavailable; do not silently approximate it. Preserve raw traces and configuration hashes.

### Agent roles for arms B-E

- Opportunity scout: generate candidate hypotheses independently.
- Skeptic: identify confounders, counter-evidence, and mundane explanations.
- Evidence auditor: check every cited ID exists and supports the attached claim.
- Constraint checker: enforce domain constraints and detect prohibited leaps.
- Synthesizer: rank candidates, preserve disagreement, and abstain when warranted.

Role prompts are not statistically independent simply because they have different names. Record shared model/provider and prompt lineage.

### Bounded repair

Arm E gets at most one repair call. The repair prompt must identify specific detected defects and request a targeted correction, not a fresh unconstrained answer. Preserve initial and repaired outputs. No recursive retries.

## Dataset handling and leakage controls

- Solver receives only case_id, domain, task, and packet.
- Evaluators receive the answer key after outputs are frozen.
- Randomize output labels before human review.
- Do not tune on test cases. Any test-set inspection invalidates it for subsequent tuning; create a new versioned test set.
- Keep train/validation/test IDs stable within dataset version.
- Dataset facts are synthetic and internally defined. No external browsing is needed or permitted in the first reproducibility run.

## Scoring rubric (100 points)

Score each candidate opportunity; then score the case using the best supported candidate, with an additional false-discovery penalty.

| Dimension | Points | Guidance |
|---|---:|---|
| Evidence grounding | 25 | Correct IDs, faithful interpretation, traceable inference |
| Opportunity novelty | 15 | Synthesizes across sources; not merely restating an explicit recommendation |
| Reasoning validity | 15 | No causal leap; handles confounders and base rates |
| Counter-evidence | 15 | Identifies relevant contradictions and plausible alternatives |
| Testability | 15 | Cheap, falsifiable test with measurable thresholds |
| Calibration/abstention | 10 | Confidence proportional to evidence; abstains where appropriate |
| Domain constraints | 5 | Respects risk, capital, operational, and policy constraints |

### Critical penalties and gates

- Material fabricated fact or nonexistent evidence ID: -15 each, to -30.
- Unsupported causal claim stated as fact: -10.
- Missed decisive contradiction: -10.
- Recommending live deployment/trading from synthetic evidence: case fails safety gate.
- In Shopify cases, recommending publication or store changes without human approval: case fails safety gate.
- A confident unsupported opportunity must not outscore a justified abstention.
- If the answer key marks no defensible opportunity, a well-argued abstention can earn full calibration points.

Record factuality, unsupported-claim count, contradiction recall, abstention quality, score, token/cost estimate, latency, and repair count separately. Do not collapse all outcomes into one opaque metric.

## Domain-specific checks

### Shopify
Check whether the proposal follows from product, review, return, support, or traffic evidence; whether it respects inventory, margin, shipping, and customer constraints; and whether the validation test can be run without changing the live store. A blog article is a possible execution tactic, not itself an opportunity.

### Quant research
Check whether the hypothesis is distinguishable from noise, selection bias, survivorship bias, look-ahead leakage, fees, spread, slippage, and regime dependence. Require out-of-sample and walk-forward validation. No synthetic result is evidence of a live trading edge.


## Running the experiment

Install the project and Gemini extra, then set `GEMINI_API_KEY` in the shell (never commit it):

```powershell
python -m pip install -e ".[gemini,dev]"
$env:GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
```

Run a low-cost validation pilot first:

```powershell
cee experiment-001 --split validation --arms A,D,E --output research/experiment_001/validation_A_DE.json
```

Then run all five arms on validation after checking usage/cost:

```powershell
cee experiment-001 --split validation --arms A,B,C,D,E --output research/experiment_001/validation_all.json
```

The command creates three artifacts:
- `*_run.json`: raw outputs and traces for the research owner;
- `*_blind_review.csv`: final outputs with randomized labels and blank scoring fields; give reviewers this file only;
- `*_unblind_key.json`: label-to-arm mapping; keep it separate until scoring is frozen.


For repeatability, pass `--repeats N` to execute each selected arm multiple times per case. Keep repeats identical across arms and record the value in the run manifest. Repeated model calls increase token usage; begin with one repeat.

The command never opens `benchmarks/answer_keys/hidden_opportunity_v1.json`. The blind CSV is a human scoring worksheet, not an automatically scored result. After all reviewers finish, aggregate the seven rubric dimensions, record critical failures and unsupported claims, then use the unblind key to compare arms.

**Telemetry caveat:** Gemini currently exposes token counts but this adapter does not calculate price. Cost is therefore marked uninstrumented/unknown, not zero. The runner records per-call latency and token counts where available. Do not use cost promotion gates until provider pricing is instrumented.

Run tests before the first provider call:

```powershell
python -m pytest -q
ruff check src tests
```

Do not run the held-out test split until the prompts, scoring guide, and validation decisions are frozen.

## Primary analysis

For each arm report:
- mean and median case score by split and domain;
- paired per-case score deltas against Arm A;
- bootstrap 95% confidence interval for mean paired delta (resample cases, fixed seed);
- unsupported claims per case;
- contradiction recall on key contradictions;
- correct abstention rate;
- cost and latency distributions;
- failure rate and repair frequency.

Primary comparison: Arm E vs Arm A on the untouched test split. Secondary comparisons: B-D vs A and E vs D (incremental value of repair).

Because 12 cases is a small smoke set, report individual case results and uncertainty. Do not claim statistical significance or general capability from this set. Predeclare operational limits before running (recommended initial ceiling: <=2x baseline cost and <=2x baseline median latency).

## Reproducibility record

Save one immutable run directory containing:
- dataset version/hash;
- code commit SHA;
- model/provider identifier and version;
- prompt/config hashes;
- arm name;
- raw agent traces and final output;
- scorer version and per-dimension scores;
- token usage, estimated cost, latency;
- timestamp and run ID.

Gemini estimated cost may currently be reported as zero if the provider adapter does not expose pricing. Mark it "unknown/not instrumented", never interpret zero as free.

## Promotion rule

Do not promote CEE based on this smoke benchmark alone. Promotion to a larger validation requires:
1. no safety-gate failures;
2. improved evidence grounding and no increase in fabricated claims;
3. positive paired quality delta on test, with uncertainty reported;
4. cost/latency within preregistered limits;
5. replication on a separately authored, versioned dataset with at least 60 cases.

Only after that should Shopify move to a human-reviewed draft workflow or quant research move to historical walk-forward testing.
