import asyncio
import os
import requests
import urllib3

from logger import get_logger

# Suppress insecure request warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")

def load_proxies(file_path=None):
    """Loads proxies from a file. Preserves scheme if present, defaults to http://.

    No process-global memoization: a cached list leaked between unrelated calls
    (and between tests) and silently ignored a changed file."""
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
            "https://duckduckgo.com", proxies=proxies, timeout=timeout, verify=False
        )
        return response.status_code == 200
    except Exception as e:
        logger.info(f"Error in {proxy} check: {e}")
        return False


async def get_working_proxies(proxies, timeout=5):
    """Filters working proxies using parallel threads."""
    tasks = [asyncio.to_thread(check_proxy, p, timeout) for p in proxies]
    results = await asyncio.gather(*tasks)
    return [p for p, is_up in zip(proxies, results) if is_up]
