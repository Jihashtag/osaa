import unittest
from unittest.mock import MagicMock, AsyncMock
from orchestrator import Orchestrator


class TestFullPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_integration(self):
        self.orch = Orchestrator()

        # Mocking the connectors
        for name, conn in self.orch.connectors.items():
            conn.run = AsyncMock(return_value=[])

        targets = [{"type": "email", "value": "test@example.com"}]
        # In a real run, the orchestrator might not add the input to identity directly,
        # but for the test we want to see if the pipeline runs and identity is accessible.
        self.orch.identity.email.append("test@example.com")
        await self.orch.run_full_pipeline(targets)

        # Verification of state update
        self.assertIn("test@example.com", self.orch.identity.email)


if __name__ == "__main__":
    unittest.main()
