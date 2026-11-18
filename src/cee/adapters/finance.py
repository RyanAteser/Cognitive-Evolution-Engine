"""Quantitative finance task adapter schema; research-only, no trading."""
from cee.adapters.base import DomainDefinition
from cee.core.schemas import Task

class FinanceAdapter:
    definition = DomainDefinition("finance", "Prediction-market and equity research.",
        ["out_of_sample_expectancy", "risk_adjusted_return", "drawdown",
         "calibration", "execution_adjusted_performance"],
        ["No live trading or order placement.",
         "Use chronological splits and an untouched holdout.",
         "Include fees, spread, slippage, liquidity, and resolution rules."])
    def build_task(self, prompt: str, metadata=None):
        return Task("finance-task", "finance", prompt, metadata or {})
    def score(self, task, output):
        return 0.0, {"requires_backtest_and_untouched_holdout": 1.0}
