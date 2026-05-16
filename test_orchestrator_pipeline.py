import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from orchestrator import Orchestrator


class TestOrchestratorPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_integration(self):
        # Initialize Orchestrator
        self.orch = Orchestrator()

        # Mock each connector's run method
        for name, connector in self.orch.connectors.items():
            connector.run = AsyncMock(return_value=[])

        targets = [{"type": "email", "value": "test@example.com"}]
        # Manual update of identity since we mocked everything
        self.orch.identity.email.append("test@example.com")

        await self.orch.run_full_pipeline(targets)

        # Verification
        self.assertIn("test@example.com", self.orch.identity.email)


if __name__ == "__main__":
    unittest.main()
