"""
Orchestrator Test Module
------------------------
Validates the core orchestration logic of the OSINT pipeline.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from orchestrator import Orchestrator


class TestOrchestrator(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the Orchestrator class.
    """

    async def test_discovery_flow(self):
        """
        Verifies that the orchestrator triggers discovery across all registered connectors.
        """
        orch = Orchestrator()

        # Mock each connector's run method
        for name, connector in orch.connectors.items():
            connector.run = AsyncMock(return_value=[])
            # If supported_types is a property, we need to mock it differently
            type(connector).supported_types = unittest.mock.PropertyMock(
                return_value=["email"]
            )

        # Execute discovery for a test target
        targets = [{"type": "email", "value": "test@example.com"}]
        await orch.run_full_pipeline(targets)

        # Ensure every connector was called
        # Check connectors called in step 1, 2, 2.1
        self.assertTrue(
            orch.connectors["search"].run.called, "SearchConnector not called"
        )
        self.assertTrue(orch.connectors["tor"].run.called, "TorConnector not called")
        self.assertTrue(
            orch.connectors["holehe"].run.called, "HoleheConnector not called"
        )
        # holmes/tookie might not be called if they don't support "email" type?
        # Holehe and Holmes seem to support email.
        self.assertTrue(
            orch.connectors["holmes"].run.called, "HolmesConnector not called"
        )
        self.assertTrue(
            orch.connectors["tookie"].run.called, "TookieConnector not called"
        )


if __name__ == "__main__":
    unittest.main()
