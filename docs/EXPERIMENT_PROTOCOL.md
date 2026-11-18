# Experimental Protocol

CEE compares candidate configurations under controlled conditions. The evaluator—not the language model—defines success.

## Controls
- Freeze task sets and data versions before runs.
- Separate evolution, validation, and final holdout data.
- Never expose holdout labels/outcomes to candidate generation.
- Compare against an unmodified baseline with equal inputs and resource budgets.
- Record model/version, prompt, settings, seed, timestamps, latency, token usage, errors, and cost.
- Repeat stochastic experiments across seeds.
- Report uncertainty and effect sizes where sample size permits.
- Preserve negative results.

## Fitness
Use task-specific objective metrics. Do not use an LLM judge as the sole evaluator when independently verified outcomes exist. For subjective tasks, pre-register a rubric and use blinded human review where feasible. Track quality, robustness, cost, latency, and failure rate separately.

## Finance safeguards
Use chronological walk-forward evaluation, realistic fees/spread/slippage, liquidity constraints, and an untouched holdout. Correct for multiple testing and report drawdown and risk-adjusted performance. Research only; no live orders.

## Shopify safeguards
Use historical or sandbox tasks. No production store mutations, publishing, price changes, ad spend, customer contact, or order changes without explicit human approval. Claim business lift only with reliable attribution.
