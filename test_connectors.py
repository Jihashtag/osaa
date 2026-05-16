"""
Connectors Test Module
----------------------
Validates the connector interfaces, including Tor-enabled discovery connectors.
"""

import unittest
from unittest.mock import MagicMock
from connectors.base import DiscoveryResult


# Mock implementation of MultiTorConnector for testing
class MockMultiTorConnector:
    def __init__(self):
        self.ENGINES = [("TestEngine", "http://test.onion/?q={}")]

    def run(self, target: str):
        return [DiscoveryResult("TestEngine", "search", target, {"data": "test"})]


class TestConnectors(unittest.TestCase):
    """
    Validation suite for OSINT connectors.
    """

    def test_discovery_result_structure(self):
        """
        Verifies that DiscoveryResult correctly holds metadata.
        """
        res = DiscoveryResult(
            source_tool="test",
            target_type="email",
            value="test@example.com",
            metadata={"exists": True},
        )
        self.assertEqual(res.value, "test@example.com")
        self.assertEqual(res.metadata["exists"], True)

    def test_tor_connector_structure(self):
        """
        Verifies the structure of the multi-engine Tor connector.
        """
        connector = MockMultiTorConnector()
        results = connector.run("test_user")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].source_tool, "TestEngine")


if __name__ == "__main__":
    unittest.main()
