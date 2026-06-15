"""Tests for the browser relevance gate (E1.2 URL skip, E1.3 content SERP gate)."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from connectors.browser import BrowserConnector

SERP_SAMPLE = "log in\nweb\nimages\nvideo\nmaps\nsearch results\nsettings\nlolla_lamb15"
PROFILE_SAMPLE = (
    "download\nif you have telegram, you can contact @lolla_lamb15 right away.\nsend message"
)


def _mock_driver(body_text, url="https://example.com/x"):
    drv = MagicMock()
    drv.current_url = url
    body = MagicMock()
    body.text = body_text
    drv.find_element.return_value = body
    return drv


class TestUrlSkip(unittest.IsolatedAsyncioTestCase):
    @patch("connectors.browser.get_report_dir", return_value="/tmp/osaa_gate")
    @patch("connectors.browser.uc.Chrome")
    async def test_discovered_serp_url_is_skipped_before_launch(self, mock_chrome, _grd):
        conn = BrowserConnector()
        conn.set_targets([{"type": "username", "value": "lolla_lamb15"}])
        res = await conn.run("https://yandex.com/search/?text=lolla_lamb15")
        self.assertEqual(res, [])
        mock_chrome.assert_not_called()  # never even started Chrome


class TestContentGate(unittest.TestCase):
    def setUp(self):
        self.conn = BrowserConnector()
        self.conn.targets = {"lolla_lamb15"}
        self.tmp = tempfile.mkdtemp()
        self.conn.res_dir = self.tmp

    def test_serp_body_rejected(self):
        self.assertIsNone(self.conn._content_checker(_mock_driver(SERP_SAMPLE)))

    def test_profile_body_accepted(self):
        out = self.conn._content_checker(_mock_driver(PROFILE_SAMPLE))
        self.assertIsNotNone(out)
        raw_path, content = out
        self.assertTrue(raw_path.endswith(".raw"))
        self.assertIn("lolla_lamb15", content)


if __name__ == "__main__":
    unittest.main()
