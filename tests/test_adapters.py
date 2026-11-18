from cee.adapters.finance import FinanceAdapter
from cee.adapters.shopify import ShopifyAdapter

def test_domain_metrics_are_distinct():
    assert "out_of_sample_expectancy" in FinanceAdapter.definition.success_metrics
    assert "task_correctness" in ShopifyAdapter.definition.success_metrics
    assert FinanceAdapter.definition.name != ShopifyAdapter.definition.name
