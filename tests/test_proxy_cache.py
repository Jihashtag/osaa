"""Verifies the orchestrator caches proxy validation within its TTL window."""

import unittest
from unittest.mock import patch

from orchestrator import Orchestrator


class TestProxyCache(unittest.IsolatedAsyncioTestCase):
    @patch("orchestrator.check_proxy")
    async def test_revalidation_is_cached_within_ttl(self, mock_check):
        mock_check.return_value = True
        orch = Orchestrator(proxies=["p1", "p2"])

        await orch._update_working_proxies()
        self.assertEqual(orch.working_proxies, ["p1", "p2"])
        calls_after_first = mock_check.call_count
        self.assertEqual(calls_after_first, 2)

        # A second call inside the TTL must not re-hit the network.
        await orch._update_working_proxies()
        self.assertEqual(mock_check.call_count, calls_after_first)

        # force=True bypasses the cache.
        await orch._update_working_proxies(force=True)
        self.assertEqual(mock_check.call_count, calls_after_first + 2)


if __name__ == "__main__":
    unittest.main()
