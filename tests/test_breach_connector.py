import asyncio
import unittest
from unittest.mock import patch

from connectors.breach import BreachConnector


class TestBackendSelection(unittest.TestCase):
    def test_auto_prefers_hibp_when_key_present(self):
        c = BreachConnector(api_key="k")
        self.assertEqual(c.effective_backend(), "hibp")

    def test_auto_falls_back_to_leakcheck_without_key(self):
        c = BreachConnector(api_key=None)
        self.assertEqual(c.effective_backend(), "leakcheck")

    def test_explicit_backend_overrides_auto(self):
        c = BreachConnector(api_key="k", backend="leakcheck")
        self.assertEqual(c.effective_backend(), "leakcheck")

    def test_unknown_backend_rejected(self):
        with self.assertRaises(ValueError):
            BreachConnector(backend="carmenSandiego")

    def test_supported_types_is_email_only(self):
        self.assertEqual(BreachConnector().supported_types, ["email"])


class TestHibpBackend(unittest.TestCase):
    def setUp(self):
        self.connector = BreachConnector(api_key="fake-key")

    @patch("connectors.breach.BreachConnector._get_hibp")
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
        self.assertEqual(results[0].confidence, 1.0)

    @patch("connectors.breach.BreachConnector._get_hibp")
    def test_run_no_breaches_is_404(self, mock_get):
        mock_get.return_value = (404, None)
        results = asyncio.run(self.connector.run("unknown@example.com"))
        self.assertEqual(results, [])

    @patch("connectors.breach.BreachConnector._get_leakcheck")
    @patch("connectors.breach.BreachConnector._get_hibp")
    def test_rejected_key_falls_back_to_leakcheck(self, mock_hibp, mock_leakcheck):
        mock_hibp.return_value = (401, None)
        mock_leakcheck.return_value = (
            200,
            {"success": True, "found": 1, "fields": ["email"], "sources": [{"name": "X", "date": "2020"}]},
        )
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata["backend"], "leakcheck")

    @patch("connectors.breach.BreachConnector._get_hibp")
    def test_run_request_exception_returns_empty(self, mock_get):
        mock_get.side_effect = Exception("network down")
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(results, [])


class TestLeakcheckBackend(unittest.TestCase):
    def setUp(self):
        self.connector = BreachConnector(api_key=None)  # auto -> leakcheck

    @patch("connectors.breach.BreachConnector._get_leakcheck")
    def test_run_hit_maps_sources(self, mock_get):
        mock_get.return_value = (
            200,
            {
                "success": True,
                "found": 42,
                "fields": ["password", "username"],
                "sources": [
                    {"name": "SiteA", "date": "2019-01"},
                    {"name": "SiteB", "date": ""},
                ],
            },
        )
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].metadata["backend"], "leakcheck")
        self.assertEqual(results[0].confidence, BreachConnector.LEAKCHECK_CONFIDENCE)
        self.assertIn("SiteA", results[0].value)

    @patch("connectors.breach.BreachConnector._get_leakcheck")
    def test_run_not_found(self, mock_get):
        mock_get.return_value = (200, {"success": True, "found": 0, "sources": []})
        results = asyncio.run(self.connector.run("unknown@example.com"))
        self.assertEqual(results, [])

    @patch("connectors.breach.BreachConnector._get_leakcheck")
    def test_run_rate_limited(self, mock_get):
        mock_get.return_value = (429, None)
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(results, [])

    @patch("connectors.breach.BreachConnector._get_leakcheck")
    def test_run_request_exception_returns_empty(self, mock_get):
        mock_get.side_effect = Exception("network down")
        results = asyncio.run(self.connector.run("test@example.com"))
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
