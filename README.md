# Cognitive Evolution Engine (CEE)

A domain-independent experimental platform for discovering which prompts, model settings, and reasoning workflows improve measurable task performance.

CEE is a research laboratory—not a promise of autonomous intelligence or profitable trading. It compares controlled candidates against baselines and keeps domain-specific success criteria separate.

## Initial foundation
- Provider-neutral model interface and optional Google Gemini adapter.
- Candidate configurations and genetic search baseline.
- Domain adapter contracts for general research, Shopify, and quantitative finance.
- SQLite experiment history.
- Offline demo and unit tests.

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

Never commit API keys. See `.env.example`.

## Commands
- `cee demo`: deterministic offline wiring demo (synthetic fitness, not a real benchmark).
- `cee run --domain general --task "..."`: call Gemini for a general task.
- `cee status`: show local SQLite experiment counts.

## Principles
1. Same task, data, model access, and resource budget for fair comparisons.
2. Never evolve against final holdout data.
3. Score outcomes, not confidence or verbosity.
4. Track quality, cost, latency, robustness, and failures separately.
5. No live trading or production Shopify changes.
6. Promote improvements only after independent validation.

## Architecture
- `cee.core`: candidate genomes and evolutionary search.
- `cee.models`: provider interfaces and model adapters.
- `cee.adapters`: domain-specific task definitions and success criteria.
- `cee.storage`: SQLite experiment history.
- `tests`: deterministic unit tests.

Gemini's standard API controls are used as documented. Token-logit, soft-prompt, embedding, and activation interventions require a model/runtime that exposes those capabilities; ordinary prompt changes do not simulate them.

See [the experiment protocol](docs/EXPERIMENT_PROTOCOL.md) and [roadmap](docs/ROADMAP.md).
