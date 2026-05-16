import requests
import logging

logger = logging.getLogger(__name__)


def load_proxies(file_path):
    """Loads proxies from a file. Preserves scheme if present, defaults to http://."""
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
    return proxies


def check_proxy(proxy, timeout=5):
    """Checks if a proxy is up by requesting duckduckgo.com."""
    try:
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        # Using duckduckgo as it's the target for ddgs anyway
        response = requests.get(
            "https://duckduckgo.com", proxies=proxies, timeout=timeout
        )
        return response.status_code == 200
    except Exception:
        return False


async def get_working_proxies(proxies):
    """Filters working proxies. In a real scenario, this could be async but requests is sync."""
    working = []
    for proxy in proxies:
        if check_proxy(proxy):
            working.append(proxy)
    return working
