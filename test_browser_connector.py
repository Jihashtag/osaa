import pytest
import logging
import asyncio
from unittest.mock import patch, MagicMock
from connectors.browser import BrowserConnector

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.asyncio
@patch("connectors.browser.get_report_dir", return_value="/tmp/osaa_test")
@patch("connectors.browser.uc.Chrome")
@patch("connectors.browser.stealth")
async def test(mock_stealth, mock_chrome, mock_report_dir):
    # Mock driver
    mock_driver = MagicMock()
    mock_chrome.return_value = mock_driver
    mock_driver.get_log.return_value = []

    # Mock response_checker to return True
    with patch("connectors.browser.response_checker", return_value=True):
        connector = BrowserConnector()
        # Mock internal methods to avoid actual network/browser activity
        with patch.object(
            connector, "_content_checker", return_value=("/tmp/test.raw", "content")
        ):
            with patch.object(connector, "_capture_media"):
                with patch("builtins.open", MagicMock()):
                    results = await connector.run("john_lamb15")
                    assert len(results) == 1
                    assert results[0].source_tool == "browser"


if __name__ == "__main__":
    asyncio.run(test())
