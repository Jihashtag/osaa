import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from proxy_utils import load_proxies, check_proxy, get_working_proxies
from orchestrator import Orchestrator
from connectors.searcher import SearchConnector
from connectors.browser import BrowserConnector


def test_load_proxies(tmp_path):
    proxy_file = tmp_path / "proxies.txt"
    proxy_file.write_text("1.2.3.4:8080\n5.6.7.8:9090\nhttp://9.10.11.12:1234")

    proxies = load_proxies(str(proxy_file))
    assert len(proxies) == 3
    assert "http://1.2.3.4:8080" in proxies
    assert "http://5.6.7.8:9090" in proxies
    assert "http://9.10.11.12:1234" in proxies


@patch("requests.get")
def test_check_proxy(mock_get):
    mock_get.return_value.status_code = 200
    assert check_proxy("http://1.2.3.4:8080") is True

    mock_get.side_effect = Exception("Timeout")
    assert check_proxy("http://1.2.3.4:8080") is False


@pytest.mark.asyncio
@patch("proxy_utils.check_proxy")
async def test_get_working_proxies(mock_check):
    # check_proxy runs concurrently across threads, so a positional
    # side_effect list would be consumed in nondeterministic order. Map the
    # verdict to the proxy value instead to keep the assertion stable.
    mock_check.side_effect = lambda proxy, *a, **k: proxy in ("p1", "p3")
    proxies = ["p1", "p2", "p3"]
    working = await get_working_proxies(proxies)
    assert working == ["p1", "p3"]


@pytest.mark.asyncio
@patch("orchestrator.check_proxy")
async def test_orchestrator_proxy_update(mock_check):
    mock_check.side_effect = [True, False]
    orchestrator = Orchestrator(proxies=["p1", "p2"])
    await orchestrator._update_working_proxies()
    assert orchestrator.working_proxies == ["p1"]


@pytest.mark.asyncio
@patch("connectors.searcher.asyncio.sleep", new_callable=AsyncMock)
@patch("connectors.searcher.DDGS")
async def test_searcher_multi_proxy(mock_ddgs, mock_sleep):
    # Mock DDGS results
    mock_instance = MagicMock()
    mock_instance.text.return_value = [{"href": "url1", "title": "t1", "body": "b1"}]
    mock_ddgs.return_value.__enter__.return_value = mock_instance

    searcher = SearchConnector()
    # We use 2 proxies for 9 dorks (by default)
    proxies = ["proxy1", "proxy2"]
    results = await searcher.run("test", proxies=proxies)

    # Check that DDGS was called with proxies
    # dorks chunked: 9 // 2 = 4. chunks: [4, 4, 1]
    # tasks: 3 tasks
    assert len(results) >= 1
    # Verify proxies were used (at least check if mock_ddgs was called with proxy argument)
    called_proxies = [call.kwargs.get("proxy") for call in mock_ddgs.call_args_list]
    assert "proxy1" in called_proxies
    assert "proxy2" in called_proxies


@pytest.mark.asyncio
@patch("connectors.browser.asyncio.sleep", new_callable=AsyncMock)
@patch("connectors.browser.stealth")
@patch("connectors.browser.uc.Chrome")
async def test_browser_proxy(mock_chrome, mock_stealth, mock_sleep):
    browser = BrowserConnector()
    # Mock driver
    mock_driver = MagicMock()
    mock_chrome.return_value = mock_driver
    mock_driver.get_log.return_value = []

    # We need to mock _content_checker to return something
    with patch("connectors.browser.get_report_dir", return_value="/tmp/test_report"):
        with patch.object(
            BrowserConnector, "_content_checker", return_value=("path", "content")
        ):
            with patch.object(BrowserConnector, "_capture_media"):
                with patch("builtins.open", MagicMock()):
                    await browser.run("http://test.com", proxy="http://proxy1:8080")

    # Check if Chrome was called with proxy option
    # options = mock_chrome.call_args.kwargs.get('options')
    # Since uc.Chrome(options=options)
    args, kwargs = mock_chrome.call_args
    options = kwargs.get("options")
    assert any("--proxy-server=http://proxy1:8080" in arg for arg in options.arguments)
