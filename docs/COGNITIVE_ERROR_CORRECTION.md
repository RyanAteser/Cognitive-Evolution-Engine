# Cognitive Error Correction: Quantum-Inspired Reliability for LLM Workflows

## Executive summary

Cognitive Error Correction (CEC) is a classical software architecture inspired by the principles of quantum error correction: redundancy, observable error signals, decoding, and fault tolerance. It does not use qubits, quantum hardware, or quantum algorithms. The research question is whether a reasoning workflow can become more reliable by generating independent attempts, detecting structured disagreement, and selectively correcting or rejecting unreliable results.

The module is an experimental subsystem of the Cognitive Evolution Engine (CEE). CEE can eventually evolve the number and diversity of reasoning paths, verification policies, evidence thresholds, decoder rules, and retry budgets against a fixed benchmark.

## Conceptual mapping

| Error-correction idea | CEE / CEC analogue | Important limitation |
|---|---|---|
| Logical information | Task objective and required answer | The task specification itself may be wrong |
| Redundant encoding | Multiple reasoning traces | LLM traces may be highly correlated |
| Physical errors | Hallucinations, arithmetic mistakes, omissions, tool failures | Errors are semantic, not bit flips |
| Syndrome | Disagreement, contradictory claims, unsupported evidence, declared failure | A disagreement is a warning, not proof |
| Decoder | Evidence-aware trace selection or abstention | The decoder can also be wrong |
| Fault tolerance | Maintain task quality despite faulty traces | Requires measured robustness under injected faults |

A majority vote is not an error corrector. A useful decoder needs evidence, task constraints, and calibrated failure signals. Three agents repeating the same unsupported claim are not three independent confirmations.

## Current implementation

The modules in src/cee/core/error_correction.py and src/cee/core/correction_workflow.py now provide:

- Claim: a normalized proposition (key, value) with evidence identifiers.
- ReasoningTrace: one agent's answer, claims, evidence references, confidence, and declared errors.
- Syndrome: a structured warning emitted by the detector.
- CorrectionReport: selected answer or abstention, per-agent scores, agreement, detected syndromes, and an auditable rationale.
- CognitiveErrorCorrector: deterministic detection and conservative decoding.\n- CognitiveCorrectionWorkflow: provider-backed diverse trace generation, strict trace parsing, evidence-aware decoding, and one bounded targeted-repair pass. The Gemini adapter can be supplied directly as the provider.

### Detection signals

1. ANSWER_DIVERGENCE: normalized answers disagree.
2. CLAIM_CONTRADICTION: traces assert different values for the same claim key.
3. DECLARED_ERROR: a trace explicitly reports a failure.

These are initial observable signals, not a complete semantic verifier. Future versions should add typed checks for arithmetic, schema validity, citation resolution, tool execution, temporal consistency, and domain-specific invariants.

### Decoder behavior

The baseline decoder scores evidence support, evidence quantity, confidence, and a deliberately limited agreement bonus. Declared errors incur a penalty. It returns no answer when evidence/reliability is too weak or the top candidates are too close. Passing available_evidence_ids lets the caller ensure that a trace cannot gain credit from references outside the task's supplied evidence set.

Confidence is only a small component of the score. It is not treated as truth. The score is an experimental ranking heuristic, not a calibrated probability.

## Proposed runtime workflow

1. **Task contract:** freeze the question, allowed sources, constraints, rubric, resource budget, and evaluation split.
2. **Diverse generation:** request multiple traces with varied strategies and, where possible, different model families or tools.
3. **Normalization:** extract answer, claims, evidence IDs, assumptions, and declared tool/calculation failures into a common schema.
4. **Syndrome detection:** compare answers and structured claims; run deterministic validators where possible.
5. **Targeted correction:** regenerate only disputed claims or rerun failed tools. Preserve original traces for audit.
6. **Decode or abstain:** select a supported result only when it clears predeclared thresholds; otherwise request human review or more evidence.
7. **Outcome evaluation:** score against hidden ground truth or a trusted rubric. Record accuracy, false correction rate, abstention quality, cost, latency, and recovery under injected faults.
8. **Evolution:** allow CEE to search workflow parameters on training/validation tasks, then evaluate the frozen winner once on a held-out test set.

## Experimental program

### Baselines

Compare all methods on identical tasks, models, tools, prompts, and resource budgets:

- Single trace, no verification.
- Multiple traces with majority vote.
- Multiple traces with evidence-aware decoding.
- Evidence-aware decoding plus targeted repair.
- CEE-evolved correction policy.

### Fault-injection matrix

Inject one failure at a time, then combinations:

- Unsupported fact or fabricated evidence identifier.
- Incorrect arithmetic result.
- Omitted constraint.
- Contradictory claim value.
- Tool timeout or malformed tool output.
- Stale observation in a time-sensitive task.
- One deliberately low-quality agent among otherwise capable agents.
- Correlated failure where every agent receives the same misleading source.

Measure clean-task accuracy and degradation as fault rate increases. A system that looks strong only when errors are independent is not robust enough.

### Metrics

- **Task accuracy / utility:** primary task-grounded outcome.
- **Error detection recall:** proportion of injected faults flagged.
- **False alarm rate:** clean traces incorrectly flagged.
- **Correction precision:** proportion of attempted corrections that improve the answer.
- **False correction rate:** proportion of originally correct answers made wrong.
- **Abstention precision and coverage:** whether abstentions concentrate on genuinely ambiguous or unsupported cases.
- **Fault recovery:** performance after one or more injected faults.
- **Cost and latency:** calls, tokens, wall time, and tool usage.

Report confidence intervals over repeated seeds. Never optimize a metric in isolation: a system can trivially reduce errors by abstaining on everything.

## Domain applications

### Quantitative research

Use independent analyses to challenge a market hypothesis, verify timestamps and contract definitions, recalculate returns and fees, and test whether a proposed edge survives out-of-sample data. The decoder must not treat wallet consensus as proof of profitability. Trading research remains read-only until separately authorized and validated.

### Shopify workflows

Cross-check product facts against catalog records, validate prices and inventory against the source of truth, and detect conflicting fulfillment or policy claims. The correction layer should never perform a production mutation merely to repair its own reasoning. Require explicit authorization and preview for consequential actions.

### General research and coding

Check factual claims against supplied sources, run tests and type checks, compare independent code reviews, and abstain when source material is insufficient. Deterministic tools should verify what they can; language-model agreement should not replace execution or external evidence.

## Research safeguards

- Keep original traces immutable; append corrections rather than overwriting.
- Separate task generation, optimization, validation, and final test sets.
- Do not let the optimizer inspect hidden labels or test answers.
- Use fixed call/token/time budgets across baselines.
- Track correlated-agent risk and shared-source dependence.
- Keep a simple baseline and rollback path.
- Treat confidence and decoder scores as heuristics until calibrated.
- Require human review for high-impact or irreversible actions.

## Roadmap

1. **Foundation (implemented):** typed traces, claims, syndrome detection, conservative evidence-aware decoder, unit tests.
2. **Generation adapters:** provider-neutral multi-trace generation with diverse strategies and strict shared task context.
3. **Semantic and deterministic validators:** arithmetic, schemas, citations, temporal checks, code execution, and domain invariants.
4. **Targeted repair:** repair only disputed claims, preserve provenance, and compare repaired output to original.
5. **Fault-injection benchmark:** repeatable datasets, fault profiles, baselines, and statistical reporting.
6. **CEE optimization:** evolve trace count/diversity, verifier selection, decoder thresholds, repair policy, and budget allocation under holdout discipline.

## Current limitations

The first implementation operates on structured traces supplied by a caller. It does not yet call multiple agents, parse free-form model responses into claims, run repair loops, or prove semantic truth. Those are subsequent research phases. The intended contribution is a falsifiable framework for testing whether error-correction-inspired workflows improve reliability at an acceptable cost.
