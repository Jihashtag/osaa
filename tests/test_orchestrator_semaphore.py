"""Behavioral tests for the Orchestrator's concurrency control and run log.

These replace earlier tests that merely grepped ``orchestrator.py`` for the
presence of strings (which passed even if the semaphore was never honoured).
"""

import asyncio
import unittest

from orchestrator import Orchestrator


class _ConcurrencyProbe:
    """Connector stub that records the peak number of overlapping runs."""

    supported_types = ["email", "username"]

    def __init__(self, tracker):
        self.tracker = tracker

    async def run(self, target, proxies=None, **kwargs):
        self.tracker["current"] += 1
        self.tracker["peak"] = max(self.tracker["peak"], self.tracker["current"])
        try:
            await asyncio.sleep(0.05)
            return []
        finally:
            self.tracker["current"] -= 1


class TestOrchestratorSemaphore(unittest.IsolatedAsyncioTestCase):
    async def test_concurrency_never_exceeds_limit(self):
        orch = Orchestrator()
        tracker = {"current": 0, "peak": 0}
        probe = _ConcurrencyProbe(tracker)

        # Launch far more tasks than the semaphore allows; peak must stay <= 5.
        tasks = [
            orch._run_with_semaphore("probe", probe, f"target{i}")
            for i in range(20)
        ]
        await asyncio.gather(*tasks)

        self.assertLessEqual(tracker["peak"], 5)
        self.assertGreater(tracker["peak"], 1)  # work actually overlapped

    async def test_execution_log_records_success_and_error(self):
        orch = Orchestrator()

        class _Ok:
            async def run(self, target, proxies=None, **kwargs):
                return [1, 2, 3]

        class _Boom:
            async def run(self, target, proxies=None, **kwargs):
                raise RuntimeError("kaboom")

        ok = await orch._run_with_semaphore("ok", _Ok(), "t")
        boom = await orch._run_with_semaphore("boom", _Boom(), "t")

        self.assertEqual(ok, [1, 2, 3])
        self.assertEqual(boom, [])  # errors are swallowed into an empty result

        statuses = {e["tool"]: e["status"] for e in orch.execution_log}
        self.assertEqual(statuses["ok"], "success")
        self.assertEqual(statuses["boom"], "error")
        ok_entry = next(e for e in orch.execution_log if e["tool"] == "ok")
        self.assertEqual(ok_entry["artifacts_count"], 3)


if __name__ == "__main__":
    unittest.main()
