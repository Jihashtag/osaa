import asyncio
import os
from typing import List, Optional, Tuple
from urllib.parse import quote

from connectors.base import BaseConnector, DiscoveryResult
from logger import get_logger

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")

# Only warn once per process instead of once per target.
_warned_no_hibp_key = False


class BreachConnector(BaseConnector):
    """
    Checks for known data breaches involving an email address.

    Two backends:
      - ``hibp``: Have I Been Pwned. Authoritative, curated, but has required
        a paid API key for the breach-check endpoint since Nov 2021
        (``--breach-api-key`` / ``HIBP_API_KEY``).
      - ``leakcheck``: leakcheck.io's free public lookup endpoint. No key
        required, but rate-limited and less curated (aggregated leaks/combo
        lists rather than only named, verified breaches) — hits from it carry
        a lower confidence than HIBP hits.

    ``backend="auto"`` (the default) uses HIBP when a key is configured and
    falls back to leakcheck otherwise, so this connector still does useful
    work with zero configuration instead of only working for HIBP
    subscribers. If a backend is unreachable it returns ``[]`` and logs why —
    it never fabricates a result.
    """

    HIBP_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{account}"
    LEAKCHECK_URL = "https://leakcheck.io/api/public"
    REQUEST_TIMEOUT = 10
    LEAKCHECK_CONFIDENCE = 0.8  # HIBP hits keep the default 1.0 (curated, verified).

    def __init__(self, api_key: str = None, backend: str = "auto"):
        self.api_key = api_key or os.environ.get("HIBP_API_KEY")
        if backend not in ("auto", "hibp", "leakcheck"):
            raise ValueError(f"unknown breach backend: {backend!r}")
        self.backend = backend

    @property
    def supported_types(self) -> List[str]:
        # Both backends are keyed on an email address.
        return ["email"]

    def effective_backend(self) -> str:
        if self.backend != "auto":
            return self.backend
        return "hibp" if self.api_key else "leakcheck"

    # -- HTTP, isolated into small blocking methods so they can run in a
    # thread and be mocked directly in tests. --

    def _get_hibp(self, target: str) -> Tuple[int, Optional[list]]:
        import requests

        url = self.HIBP_URL.format(account=quote(target, safe=""))
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

    def _get_leakcheck(self, target: str) -> Tuple[int, Optional[dict]]:
        import requests

        resp = requests.get(
            self.LEAKCHECK_URL,
            params={"check": target},
            headers={"user-agent": "osaa-osint-tool"},
            timeout=self.REQUEST_TIMEOUT,
        )
        try:
            body = resp.json()
        except ValueError:
            body = None
        return resp.status_code, body

    # -- Backend-specific run paths --

    async def _run_hibp(self, target: str) -> List[DiscoveryResult]:
        try:
            status, breaches = await asyncio.to_thread(self._get_hibp, target)
        except Exception as e:
            logger.error(f"[x] breach(hibp): request failed for {target}: {e}")
            return []

        if status == 404:
            return []  # no known breaches for this account
        if status == 401:
            logger.error(
                "[x] breach(hibp): API key rejected (401); falling back to leakcheck"
            )
            return await self._run_leakcheck(target)
        if status == 429:
            logger.warning(f"[x] breach(hibp): rate-limited (429) on {target}")
            return []
        if status != 200 or breaches is None:
            logger.error(f"[x] breach(hibp): HTTP {status} for {target}")
            return []

        results = [
            DiscoveryResult(
                source_tool="breach",
                target_type="breach_record",
                value=f"{b.get('Name', 'unknown')} ({b.get('BreachDate', 'unknown date')})",
                metadata={
                    "breach_name": b.get("Name", "unknown"),
                    "date": b.get("BreachDate", "unknown date"),
                    "data_classes": ", ".join(b.get("DataClasses", [])),
                    "email": target,
                    "backend": "hibp",
                },
                confidence=1.0,
            )
            for b in breaches
        ]
        if results:
            logger.info(f"[✓] breach(hibp): {target} found in {len(results)} breach(es)")
        return results

    async def _run_leakcheck(self, target: str) -> List[DiscoveryResult]:
        try:
            status, body = await asyncio.to_thread(self._get_leakcheck, target)
        except Exception as e:
            logger.error(f"[x] breach(leakcheck): request failed for {target}: {e}")
            return []

        if status == 429:
            logger.warning(f"[x] breach(leakcheck): rate-limited (429) on {target}")
            return []
        if status != 200 or body is None:
            logger.error(f"[x] breach(leakcheck): HTTP {status} for {target}")
            return []
        if not body.get("success") or not body.get("found"):
            return []

        fields = ", ".join(body.get("fields", []) or [])
        results = [
            DiscoveryResult(
                source_tool="breach",
                target_type="breach_record",
                value=f"{s.get('name', 'unknown source')} ({s.get('date') or 'unknown date'})",
                metadata={
                    "breach_name": s.get("name", "unknown source"),
                    "date": s.get("date") or "unknown date",
                    "data_classes": fields,
                    "email": target,
                    "backend": "leakcheck",
                },
                confidence=self.LEAKCHECK_CONFIDENCE,
            )
            for s in (body.get("sources") or [])
        ]
        if results:
            logger.info(
                f"[✓] breach(leakcheck): {target} found in {len(results)} source(s)"
            )
        return results

    async def run(
        self, target: str, proxies: List[str] = None, **kwargs
    ) -> List[DiscoveryResult]:
        global _warned_no_hibp_key
        backend = self.effective_backend()
        if self.backend == "auto" and not self.api_key and not _warned_no_hibp_key:
            logger.info(
                "[*] breach: no HIBP key configured (--breach-api-key / "
                "HIBP_API_KEY) — using the free leakcheck.io backend instead"
            )
            _warned_no_hibp_key = True

        if backend == "hibp":
            return await self._run_hibp(target)
        return await self._run_leakcheck(target)
