"""Integration coverage for the discovery cache wired into
Orchestrator._run_with_semaphore (see utils/cache.py for the hit policy)."""

import asyncio
import contextlib
import io
import tempfile
import unittest

from connectors.base import DiscoveryResult
from orchestrator import Orchestrator
from utils.cache import CacheManager


def _tmp_cache():
    return CacheManager(db_path=tempfile.mktemp(suffix=".sqlite"))


def _results(n):
    return [DiscoveryResult("holehe", "account", f"service{i}", {}) for i in range(n)]


class _CountingConnector:
    supported_types = ["email", "username"]

    def __init__(self, results=None, error=None):
        self.results = results if results is not None else []
        self.error = error
        self.calls = 0

    async def run(self, target, proxies=None, **kwargs):
        self.calls += 1
        if self.error:
            raise self.error
        return self.results


class TestOrchestratorCacheDisabledByDefault(unittest.IsolatedAsyncioTestCase):
    async def test_bare_orchestrator_never_touches_cache(self):
        orch = Orchestrator()  # no cache/use_cache passed
        self.assertIsNone(orch.cache)
        conn = _CountingConnector(results=_results(2))
        await orch._run_with_semaphore("probe", conn, "t")
        await orch._run_with_semaphore("probe", conn, "t")
        self.assertEqual(conn.calls, 2)  # re-fetched every time: no cache


class TestOrchestratorCacheHits(unittest.IsolatedAsyncioTestCase):
    async def test_pertinent_result_is_reused_across_calls(self):
        orch = Orchestrator(cache=_tmp_cache())
        conn = _CountingConnector(results=_results(3))

        r1 = await orch._run_with_semaphore("holehe", conn, "a@b.com")
        r2 = await orch._run_with_semaphore("holehe", conn, "a@b.com")

        self.assertEqual(conn.calls, 1)  # second call served from cache
        self.assertEqual(len(r1), 3)
        self.assertEqual(len(r2), 3)

    async def test_different_target_is_not_a_cache_hit(self):
        orch = Orchestrator(cache=_tmp_cache())
        conn = _CountingConnector(results=_results(1))

        await orch._run_with_semaphore("holehe", conn, "a@b.com")
        await orch._run_with_semaphore("holehe", conn, "c@d.com")

        self.assertEqual(conn.calls, 2)

    async def test_empty_result_is_cached_within_ttl(self):
        orch = Orchestrator(cache=_tmp_cache())
        conn = _CountingConnector(results=[])

        await orch._run_with_semaphore("holehe", conn, "a@b.com")
        await orch._run_with_semaphore("holehe", conn, "a@b.com")

        self.assertEqual(conn.calls, 1)  # negative result also skips re-fetch

    async def test_error_is_never_cached_and_is_retried(self):
        orch = Orchestrator(cache=_tmp_cache())
        conn = _CountingConnector(error=RuntimeError("proxy down"))

        r1 = await orch._run_with_semaphore("holehe", conn, "a@b.com")
        r2 = await orch._run_with_semaphore("holehe", conn, "a@b.com")

        self.assertEqual(r1, [])
        self.assertEqual(r2, [])
        self.assertEqual(conn.calls, 2)  # retried both times, never cached

    async def test_cache_hit_is_logged_in_execution_log(self):
        orch = Orchestrator(cache=_tmp_cache())
        conn = _CountingConnector(results=_results(1))

        await orch._run_with_semaphore("holehe", conn, "a@b.com")
        await orch._run_with_semaphore("holehe", conn, "a@b.com")

        statuses = [e["status"] for e in orch.execution_log if e["tool"] == "holehe"]
        self.assertEqual(statuses, ["success", "cache_hit"])


class TestCacheSummary(unittest.TestCase):
    def test_summary_counts_by_status(self):
        orch = Orchestrator(cache=_tmp_cache())
        orch.execution_log = [
            {"tool": "a", "status": "success"},
            {"tool": "b", "status": "cache_hit"},
            {"tool": "c", "status": "cache_hit"},
            {"tool": "d", "status": "error"},
        ]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            orch._print_cache_summary()
        self.assertIn("2/4", buf.getvalue())
        self.assertIn("1 fetched live", buf.getvalue())
        self.assertIn("1 errored", buf.getvalue())

    def test_summary_reports_disabled_when_no_cache(self):
        orch = Orchestrator()  # use_cache defaults False
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            orch._print_cache_summary()
        self.assertIn("disabled", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
