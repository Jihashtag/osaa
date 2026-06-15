"""Offline unit tests for SearchConnector result handling.

These exercise dedupe, local-noise filtering, robust row parsing and the
confidence signal without touching the network (the live end-to-end test lives
in test_searcher.py behind @pytest.mark.network).
"""

import unittest

from connectors.searcher import SearchConnector
from connectors.base import DiscoveryResult


class TestSearcherUnit(unittest.TestCase):
    def setUp(self):
        self.s = SearchConnector()

    def test_rows_to_results_skips_noise_and_malformed(self):
        rows = [
            {"href": "https://example.com/a", "title": "A", "body": "b"},
            {"href": "https://host/repo/.git/config"},  # local noise -> dropped
            {"title": "no href"},                         # malformed  -> dropped
            {"href": "orchestrator.py"},                  # source file -> dropped
        ]
        out = self.s._rows_to_results(rows, query='"x"', confidence=0.7)
        self.assertEqual([r.value for r in out], ["https://example.com/a"])
        self.assertEqual(out[0].confidence, 0.7)
        self.assertEqual(out[0].metadata["query"], '"x"')

    def test_rows_to_results_uses_get_for_missing_fields(self):
        out = self.s._rows_to_results(
            [{"href": "https://example.com/x"}], query="q", confidence=0.5
        )
        self.assertEqual(out[0].metadata["title"], "")
        self.assertEqual(out[0].metadata["snippet"], "")

    def test_dedupe_keeps_highest_confidence(self):
        url = "https://example.com/dup"
        results = [
            DiscoveryResult("searcher", "url", url, {}, confidence=0.4),
            DiscoveryResult("searcher", "url", url, {}, confidence=0.7),
            DiscoveryResult("searcher", "url", "https://other", {}, confidence=0.5),
        ]
        deduped = self.s._dedupe(results)
        by_url = {r.value: r for r in deduped}
        self.assertEqual(len(deduped), 2)
        self.assertEqual(by_url[url].confidence, 0.7)

    def test_build_query_kwargs_strips_http_scheme(self):
        self.assertEqual(
            self.s._build_query_kwargs("http://1.2.3.4:8080")["proxy"], "1.2.3.4:8080"
        )
        self.assertNotIn("proxy", self.s._build_query_kwargs(None))


if __name__ == "__main__":
    unittest.main()
