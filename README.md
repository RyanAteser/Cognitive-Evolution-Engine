# Cognitive Evolution Engine (CEE)

A domain-independent experimental platform for discovering which prompts, model settings, and reasoning workflows improve measurable task performance.

CEE is a research laboratory—not a promise of autonomous intelligence or profitable trading. It compares controlled candidates against baselines and keeps domain-specific success criteria separate.

## Initial foundation
- Provider-neutral model interface and optional Google Gemini adapter.
- Candidate configurations and genetic search baseline.
- Domain adapter contracts for general research, Shopify, and quantitative finance.
- SQLite experiment history.
- Offline demo and unit tests.

## Cognitive Error Correction (new research module)

CEE now includes a quantum-inspired **classical** error-correction layer. It treats multiple reasoning attempts as redundant traces, detects disagreement and contradictory claims (the syndrome), and uses evidence-aware decoding to select a result or abstain.

This is inspired by the architecture of quantum error correction—not quantum computing. It uses no qubits or quantum hardware, and it does not assume majority vote equals truth. The research goal is to measure whether structured redundancy, error detection, targeted repair, and conservative decoding improve reliability under controlled fault injection.

See the in-depth [Cognitive Error Correction research guide](docs/COGNITIVE_ERROR_CORRECTION.md) for the conceptual mapping and research protocol, plus the [Gemini-backed correction workflow guide](docs/GEMINI_CORRECTION_WORKFLOW.md) for multi-trace generation, evidence-aware decoding, targeted repair, setup, and limitations.

## Quick start (Python 3.11+)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cee demo
pytest
```

Optional Gemini integration:

```powershell
$env:GEMINI_API_KEY = "your-key"
$env:CEE_MODEL = "gemini-2.5-flash"
cee run --domain general --task "Explain precision versus recall."
```

Never commit API keys. See .env.example.

## Commands
- cee demo: deterministic offline wiring demo (synthetic fitness, not a real benchmark).
- cee run --domain general --task "…": call Gemini for a general task.
- cee status: show local SQLite experiment counts.

## Principles
1. Same task, data, model access, and resource budget for fair comparisons.
2. Never evolve against final holdout data.
3. Score outcomes, not confidence or verbosity.
4. Track quality, cost, latency, robustness, and failures separately.
5. No live trading or production Shopify changes.
6. Promote improvements only after independent validation.

## Architecture
- cee.core: candidate genomes, evolutionary search, and cognitive error correction.
- cee.models: provider interfaces and model adapters.
- cee.adapters: domain-specific task definitions and success criteria.
- cee.storage: SQLite experiment history.
- tests: deterministic unit tests.

Gemini's standard API controls are used as documented. Token-logit, soft-prompt, embedding, and activation interventions require a model/runtime that exposes those capabilities; ordinary prompt changes do not simulate them.

See the [benchmark protocol](docs/BENCHMARK_PROTOCOL.md) for dataset splits, paired comparisons, statistical checks, ablations, domain suites, and promotion rules.
