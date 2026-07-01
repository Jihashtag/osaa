import asyncio
import unittest
from unittest.mock import MagicMock, patch

from connectors.breach import BreachConnector


class TestBreachConnectorNoKey(unittest.TestCase):
    """Without an API key the connector must skip cleanly, not fabricate a hit."""

    def setUp(self):
        self.connector = BreachConnector(api_key=None)

    def test_skips_without_key(self):
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(results, [])


class TestBreachConnectorWithKey(unittest.TestCase):
    def setUp(self):
        self.connector = BreachConnector(api_key="fake-key")

    @patch("connectors.breach.BreachConnector._get")
    def test_run_hit_maps_breach_fields(self, mock_get):
        mock_get.return_value = (
            200,
            [
                {
                    "Name": "Adobe",
                    "BreachDate": "2013-10-04",
                    "DataClasses": ["Email addresses", "Passwords"],
                }
            ],
        )
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_tool, "breach")
        self.assertIn("Adobe", results[0].value)
        self.assertEqual(results[0].metadata["breach_name"], "Adobe")

    @patch("connectors.breach.BreachConnector._get")
    def test_run_no_breaches_is_404(self, mock_get):
        mock_get.return_value = (404, None)
        results = asyncio.run(self.connector.run("unknown@example.com"))
        self.assertEqual(results, [])

    @patch("connectors.breach.BreachConnector._get")
    def test_run_bad_key_is_401(self, mock_get):
        mock_get.return_value = (401, None)
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(results, [])

    @patch("connectors.breach.BreachConnector._get")
    def test_run_request_exception_returns_empty(self, mock_get):
        mock_get.side_effect = Exception("network down")
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(results, [])

    def test_supported_types_is_email_only(self):
        self.assertEqual(self.connector.supported_types, ["email"])


if __name__ == "__main__":
    unittest.main()
