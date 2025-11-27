import unittest

from prometheus_client import REGISTRY

from app.core.metrics import observe_search


def sample(metric_name: str, labels: dict | None = None) -> float:
    """Return a metric sample value or 0.0 when unset."""
    value = REGISTRY.get_sample_value(metric_name, labels=labels)
    return float(value) if value is not None else 0.0


class MetricsTest(unittest.TestCase):
    def test_observe_search_records_counters(self):
        labels = {"container": "expressionist-art", "mode": "hybrid", "status": "success"}
        before_requests = sample("llc_search_requests_total", labels)
        before_total_latency = sample("llc_search_total_latency_seconds_sum")
        before_results_returned = sample("llc_search_results_returned_sum", {"mode": "hybrid"})
        before_bm25_latency = sample("llc_search_stage_latency_seconds_sum", {"stage": "bm25"})
        before_vector_latency = sample("llc_search_stage_latency_seconds_sum", {"stage": "vector"})

        observe_search(
            "hybrid",
            {"bm25_ms": 20, "vector_ms": 30, "total_ms": 80},
            returned=4,
            container_ids=[labels["container"]],
            issues=[],
        )

        self.assertEqual(sample("llc_search_requests_total", labels), before_requests + 1)
        self.assertGreater(sample("llc_search_total_latency_seconds_sum"), before_total_latency)
        self.assertGreaterEqual(
            sample("llc_search_results_returned_sum", {"mode": "hybrid"}), before_results_returned + 4
        )
        self.assertGreater(sample("llc_search_stage_latency_seconds_sum", {"stage": "bm25"}), before_bm25_latency)
        self.assertGreater(sample("llc_search_stage_latency_seconds_sum", {"stage": "vector"}), before_vector_latency)


if __name__ == "__main__":
    unittest.main()
