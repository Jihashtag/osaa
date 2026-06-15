"""E3.2 page-load timeout + E3.3 bot-block backoff in BrowserConnector."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from selenium.common.exceptions import TimeoutException
from connectors.browser import BrowserConnector


def _driver(current_url="https://example.com/x"):
    d = MagicMock()
    d.current_url = current_url
    d.get_log.return_value = []
    d.find_elements.return_value = []
    return d


class TestPageLoadTimeout(unittest.IsolatedAsyncioTestCase):
    @patch("connectors.browser.asyncio.sleep", new_callable=AsyncMock)
    @patch("connectors.browser.get_report_dir", return_value="/tmp/osaa_perf")
    @patch("connectors.browser.stealth")
    @patch("connectors.browser.uc.Chrome")
    async def test_timeout_returns_empty_and_quits(self, mock_chrome, _s, _g, _sl):
        d = _driver()
        d.get.side_effect = TimeoutException("slow")
        mock_chrome.return_value = d
        conn = BrowserConnector()
        conn.set_targets([{"type": "username", "value": "lolla_lamb15"}])
        res = await conn.run("https://example.com/profile")
        self.assertEqual(res, [])
        d.quit.assert_called()  # no leaked driver


class TestBotBlockBackoff(unittest.IsolatedAsyncioTestCase):
    @patch("connectors.browser.asyncio.sleep", new_callable=AsyncMock)
    @patch("connectors.browser.get_report_dir", return_value="/tmp/osaa_perf")
    @patch("connectors.browser.stealth")
    @patch("connectors.browser.uc.Chrome")
    async def test_block_records_domain(self, mock_chrome, _s, _g, _sl):
        d = _driver(current_url="https://www.google.com/sorry/index?continue=x")
        mock_chrome.return_value = d
        conn = BrowserConnector()
        conn.set_targets([{"type": "username", "value": "lolla_lamb15"}])
        blocked = set()
        res = await conn.run("https://www.google.com/search/x", blocked_domains=blocked)
        # google.com/search is a SERP -> skipped before launch; force a non-SERP host
        res = await conn.run("https://news.example.org/p", blocked_domains=blocked)
        self.assertEqual(res, [])
        self.assertIn("google.com", blocked)

    @patch("connectors.browser.uc.Chrome")
    async def test_blocked_domain_skipped_before_launch(self, mock_chrome):
        with patch("connectors.browser.get_report_dir", return_value="/tmp/osaa_perf"):
            conn = BrowserConnector()
            conn.set_targets([{"type": "username", "value": "lolla_lamb15"}])
            res = await conn.run(
                "https://news.example.org/p", blocked_domains={"news.example.org"}
            )
        self.assertEqual(res, [])
        mock_chrome.assert_not_called()


class TestDriverReuse(unittest.IsolatedAsyncioTestCase):
    @patch("connectors.browser.asyncio.sleep", new_callable=AsyncMock)
    @patch("connectors.browser.get_report_dir", return_value="/tmp/osaa_perf")
    @patch("connectors.browser.stealth")
    @patch("connectors.browser.uc.Chrome")
    async def test_run_many_uses_one_driver(self, mock_chrome, _s, _g, _sl):
        d = _driver()
        mock_chrome.return_value = d
        conn = BrowserConnector()
        conn.set_targets([{"type": "username", "value": "lolla_lamb15"}])
        urls = [
            "https://t.me/a",
            "https://lolchess.gg/profile/b",
            "https://news.example.org/c",
        ]
        with patch.object(conn, "_visit", new_callable=AsyncMock, return_value=[]) as visit:
            await conn.run_many(urls)
        # ONE Chrome launch for the whole batch, three visits, one quit.
        self.assertEqual(mock_chrome.call_count, 1)
        self.assertEqual(visit.call_count, 3)
        d.quit.assert_called_once()

    @patch("connectors.browser.uc.Chrome")
    async def test_run_many_all_serp_does_not_launch(self, mock_chrome):
        with patch("connectors.browser.get_report_dir", return_value="/tmp/osaa_perf"):
            conn = BrowserConnector()
            conn.set_targets([{"type": "username", "value": "u"}])
            res = await conn.run_many(
                ["https://google.com/search?q=a", "https://bing.com/search?q=b"]
            )
        self.assertEqual(res, [])
        mock_chrome.assert_not_called()


if __name__ == "__main__":
    unittest.main()
