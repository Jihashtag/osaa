import unittest
import asyncio
from unittest.mock import MagicMock
from osaa.orchestrator import Orchestrator
from osaa.models import Knowledge


class TestOrchestratorKnowledge(unittest.TestCase):
    def test_init_with_knowledge(self):
        knowledge = Knowledge(identity={"email": "test@example.com"})
        orchestrator = Orchestrator(proxies=[], knowledge=knowledge)
        self.assertEqual(orchestrator.knowledge.identity["email"], "test@example.com")

    def test_run_with_knowledge(self):
        knowledge = Knowledge(identity={"username": "testuser"})
        orchestrator = Orchestrator(proxies=[])

        # Using a mock for run_full_pipeline logic or just checking the assignment
        async def mock_run():
            await orchestrator.run_full_pipeline(targets=[], knowledge=knowledge)
            return orchestrator.knowledge

        res = asyncio.run(mock_run())
        self.assertEqual(res.identity["username"], "testuser")


if __name__ == "__main__":
    unittest.main()
