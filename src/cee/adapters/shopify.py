"""Shopify task adapter schema; performs no live store mutations."""
from cee.adapters.base import DomainDefinition
from cee.core.schemas import Task

class ShopifyAdapter:
    definition = DomainDefinition("shopify", "Ecommerce research and decision support.",
        ["task_correctness", "policy_compliance", "business_outcome"],
        ["Research-only by default; no production mutations.",
         "Require human approval for consequential store actions.",
         "Do not claim conversion or profit lift without reliable attribution."])
    def build_task(self, prompt: str, metadata=None):
        return Task("shopify-task", "shopify", prompt, metadata or {})
    def score(self, task, output):
        return 0.0, {"requires_store_specific_rubric_or_outcome_data": 1.0}
