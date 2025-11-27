import unittest

from app.services.search import _latency_budget_info


class SearchLatencyBudgetTest(unittest.TestCase):
    def test_within_budget_has_no_issue(self):
        diagnostics, issues = _latency_budget_info(total_ms=100, budget=200)
        self.assertEqual(diagnostics["latency_budget_ms"], 200)
        self.assertEqual(diagnostics["latency_over_budget_ms"], 0)
        self.assertEqual(issues, [])

    def test_over_budget_sets_issue(self):
        diagnostics, issues = _latency_budget_info(total_ms=350, budget=200)
        self.assertEqual(diagnostics["latency_over_budget_ms"], 150)
        self.assertIn("LATENCY_BUDGET_EXCEEDED", issues)


if __name__ == "__main__":
    unittest.main()
