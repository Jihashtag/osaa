import asyncio
import os
from typing import List
from urllib.parse import quote

from connectors.base import BaseConnector, DiscoveryResult
from logger import get_logger

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")

# Only warn once per process instead of once per target — HIBP requires a key
# per query, so a missing key would otherwise spam the log on every run.
_warned_no_key = False


class BreachConnector(BaseConnector):
    """
    Checks Have I Been Pwned (HIBP) for known data breaches involving an
    email address.

    HIBP has required a paid API key for the breach-check endpoint since
    Nov 2021 (``--breach-api-key`` / ``HIBP_API_KEY`` env var). Without a key
    this connector skips cleanly and says so once, the same way the Tor
    connector skips when the daemon isn't running — no network call, no
    fabricated results.
    """

    API_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{account}"
    REQUEST_TIMEOUT = 10

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("HIBP_API_KEY")

    @property
    def supported_types(self) -> List[str]:
        # HIBP's breachedaccount lookup is keyed on email address.
        return ["email"]

    def _get(self, target: str):
        """Blocking HTTP GET, isolated so it can run in a thread and be
        mocked in tests. Returns (status_code, parsed_json_or_None)."""
        import requests

        url = self.API_URL.format(account=quote(target, safe=""))
        headers = {"hibp-api-key": self.api_key, "user-agent": "osaa-osint-tool"}
        resp = requests.get(
            url,
            headers=headers,
            params={"truncateResponse": "false"},
            timeout=self.REQUEST_TIMEOUT,
        )
        try:
            body = resp.json() if resp.status_code == 200 else None
        except ValueError:
            body = None
        return resp.status_code, body

    async def run(
        self, target: str, proxies: List[str] = None, **kwargs
    ) -> List[DiscoveryResult]:
        global _warned_no_key
        if not self.api_key:
            if not _warned_no_key:
                logger.warning(
                    "[!] breach: no API key configured (--breach-api-key / "
                    "HIBP_API_KEY) — skipping breach lookups"
                )
                _warned_no_key = True
            return []

        try:
            status, breaches = await asyncio.to_thread(self._get, target)
        except Exception as e:
            logger.error(f"[x] breach: request failed for {target}: {e}")
            return []

        if status == 404:
            return []  # no known breaches for this account
        if status == 401:
            logger.error("[x] breach: HIBP rejected the API key (401)")
            return []
        if status == 429:
            logger.warning(f"[x] breach: rate-limited by HIBP (429) on {target}")
            return []
        if status != 200 or breaches is None:
            logger.error(f"[x] breach: HIBP HTTP {status} for {target}")
            return []

        results = []
        for b in breaches:
            name = b.get("Name", "unknown")
            date = b.get("BreachDate", "unknown date")
            results.append(
                DiscoveryResult(
                    source_tool="breach",
                    target_type="breach_record",
                    value=f"{name} ({date})",
                    metadata={
                        "breach_name": name,
                        "date": date,
                        "data_classes": ", ".join(b.get("DataClasses", [])),
                        "email": target,
                    },
                    confidence=1.0,
                )
            )
        if results:
            logger.info(f"[✓] breach: {target} found in {len(results)} breach(es)")
        return results
