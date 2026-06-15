"""E5.2 — Orchestrator.plan() returns a network-free execution plan."""

import unittest
from unittest.mock import patch

from orchestrator import Orchestrator


class TestOrchestratorPlan(unittest.TestCase):
    def test_plan_lists_connectors_by_type_and_excludes_browser(self):
        orch = Orchestrator()
        plan = orch.plan([{"type": "email", "value": "a@b.com"}])
        self.assertEqual(len(plan), 1)
        entry = plan[0]
        self.assertEqual(entry["type"], "email")
        self.assertIn("holehe", entry["connectors"])
        self.assertIn("search", entry["connectors"])
        self.assertNotIn("browser", entry["connectors"])

    def test_plan_skips_empty_values_and_does_no_network(self):
        orch = Orchestrator()
        # Spy: no connector.run must be called during planning.
        with patch.object(orch, "_run_with_semaphore") as run_spy:
            plan = orch.plan(
                [{"type": "username", "value": "u"}, {"type": "email", "value": ""}]
            )
            run_spy.assert_not_called()
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["value"], "u")


if __name__ == "__main__":
    unittest.main()
