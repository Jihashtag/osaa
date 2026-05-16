import os
import requests

from logger import get_logger
from unittest.mock import patch

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")

PROXIES = None

def load_proxies(file_path=None):
    """Loads proxies from a file. Preserves scheme if present, defaults to http://."""

    global PROXIES

    if PROXIES is not None:
        return PROXIES
    proxies = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    if "://" in line:
                        proxies.append(line)
                    else:
                        proxies.append(f"http://{line}")
    except Exception as e:
        logger.error(f"Error loading proxy list: {e}")
    PROXIES = proxies
    return proxies


def check_proxy(proxy, timeout=5):
    """Checks if a proxy is up by requesting duckduckgo.com."""
    try:
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        # Using duckduckgo as it's the target for ddgs anyway
        with patch("urllib3.connectionpool.warnings.warn", return_value=None):
            response = requests.get(
                "https://duckduckgo.com",
                proxies=proxies,
                timeout=timeout,
                verify=False
            )
            return response.status_code == 200
    except Exception as e:
        logger.info(f"Error in {proxy} check: {e}")
        return False


async def get_working_proxies(proxies):
    """Filters working proxies. In a real scenario, this could be async but requests is sync."""
    working = []
    for proxy in proxies:
        if check_proxy(proxy):
            working.append(proxy)
    return working
