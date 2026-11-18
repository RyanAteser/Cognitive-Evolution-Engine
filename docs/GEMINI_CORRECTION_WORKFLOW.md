# Gemini-backed Cognitive Correction Workflow

This phase connects the existing trace detector/decoder to the provider interface. It is an initial orchestration harness, not a claim that model consensus establishes truth.

## Run it

Install the optional Gemini extra and configure the key in PowerShell:

```powershell
python -m pip install -e ".[gemini,dev]"
$env:GEMINI_API_KEY = "your-key"
$env:CEE_MODEL = "gemini-2.5-flash"
```

Example Python entry point:

```python
from cee.core.correction_workflow import CognitiveCorrectionWorkflow
from cee.core.schemas import Task
from cee.models.gemini import GeminiProvider

workflow = CognitiveCorrectionWorkflow(GeminiProvider(), max_agents=4)
task = Task(
    task_id="example-001",
    domain="general",
    prompt="Compare two claims using the source excerpts supplied below.",
    metadata={},
)
run = workflow.run(task, available_evidence_ids={"source-1", "source-2"})
print(run.report.answer or "ABSTAIN")
print(run.report.syndromes)
print(run.generation_calls)
```

The task prompt must include the actual evidence content and the exact identifiers in the allowlist. An allowlist validates references; it does not independently validate whether a cited source supports a claim.

## Execution design

- Four distinct strategy prompts are used: independent solver, skeptical reviewer, evidence auditor, and constraint checker.
- Each attempt must return a structured JSON trace. Invalid output raises a parsing error rather than silently becoming a low-quality trace.
- The existing deterministic decoder evaluates the original traces against the caller-supplied evidence identifier set.
- If syndromes are present, one bounded targeted-repair call is made. The repair trace is appended; original traces remain available and unchanged.
- The final report is decoded across the initial and repair traces. The run object records call count and preserves all inputs for audit.
- Repair can be disabled. The workflow does not retry indefinitely.

## Important limits

1. Strategy prompts do not guarantee statistical independence. Same-model outputs can share failure modes.
2. The parser validates shape and types, not semantic correctness.
3. Evidence identifier membership is not citation entailment. A later verifier must inspect source passages.
4. The current heuristic decoder is not calibrated. Its score is not a probability.
5. This harness does not execute tools, place trades, or mutate Shopify data.
6. A real benchmark still needs ground truth, fault injection, repeated runs, cost/latency tracking, and held-out evaluation.

## Fault-injection protocol

The next benchmark should preserve clean traces and generate paired corrupted copies with controlled faults: unsupported evidence IDs, conflicting claim values, malformed JSON, incorrect numeric claims, missing constraints, stale source data, and shared misleading sources. Report detection recall, false alarms, correction precision, false correction rate, abstention coverage, task accuracy, cost, and latency. A correction counts as successful only when checked against task ground truth—not because the repair agent agrees with the original agents.
