import asyncio
import os
import random

from ddgs import DDGS
from logger import get_logger
from connectors.base import BaseConnector, DiscoveryResult
from blocklist import is_local_noise
from typing import List

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class SearchConnector(BaseConnector):
    # Tiered Dorks: Start specific, broaden if no results

    @property
    def supported_types(self) -> List[str]:
        return ["query", "username", "email", "fullname"]

    async def run(
        self,
        target: str,
        proxies: List[str] = None,
        max_results: int = 10,
        **kwargs,
    ) -> List[DiscoveryResult]:
        dorks = (
            [
                f'"{target}"',
                f'"{target}" profile',
                f'"{target}" site:instagram.com',
                f'"{target}" site:facebook.com',
                f'"{target}" site:linkedin.com',
                f'"{target}" site:reddit.com',
                f'"{target}@gmail.com"',
                f'"{target}@hotmail.com"',
                f'"{target}@yahoo.com"',
            ]
            if ":" not in target and "@" not in target
            else [f'"{target}"', f'"{target}" profile', f"{target}"]
        )

        if not proxies:
            return await self._run_dorks(dorks, None, max_results)

        # Split dorks among proxies
        num_proxies = len(proxies)
        chunk_size = max(1, len(dorks) // num_proxies)
        dork_chunks = [
            dorks[i : i + chunk_size] for i in range(0, len(dorks), chunk_size)
        ]

        tasks = []
        for idx, chunk in enumerate(dork_chunks):
            # Rotate proxies if more chunks than proxies
            proxy = proxies[idx % num_proxies]
            tasks.append(self._run_dorks(chunk, proxy, max_results))

        results = await asyncio.gather(*tasks)
        # Flatten then deduplicate by URL across all dorks/proxies.
        flat = [item for sublist in results for item in sublist]
        return self._dedupe(flat)

    @staticmethod
    def _dedupe(results: List[DiscoveryResult]) -> List[DiscoveryResult]:
        """Collapses results sharing the same URL, keeping the highest
        confidence sighting (tiered dorks overlap heavily)."""
        best = {}
        for r in results:
            current = best.get(r.value)
            if current is None or r.confidence > current.confidence:
                best[r.value] = r
        return list(best.values())

    @staticmethod
    def _build_query_kwargs(proxy: str) -> dict:
        kwargs = {"verify": False}
        if proxy is not None:
            # ddgs wants a bare host:port for http proxies. Strip the scheme
            # with removeprefix ("http://" is 7 chars; the old proxy[8:] ate
            # the first character of the address).
            kwargs["proxy"] = proxy.removeprefix("http://")
        return kwargs

    def _rows_to_results(
        self, rows: list, query: str, confidence: float
    ) -> List[DiscoveryResult]:
        """Maps raw DDGS rows to DiscoveryResults, skipping local noise and
        malformed rows. Uses .get() so one bad row can't abort the batch."""
        out = []
        for r in rows:
            url = r.get("href")
            if not url or is_local_noise(url):
                continue
            out.append(
                DiscoveryResult(
                    "searcher",
                    "url",
                    url,
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "query": query,
                    },
                    confidence=confidence,
                )
            )
        return out

    @staticmethod
    def _ddgs_text(kwargs: dict, query: str, max_results: int) -> list:
        """Blocking DDGS call, intended to run in a worker thread."""
        with DDGS(**kwargs) as ddgs:
            return list(
                ddgs.text(query, safesearch="off", max_results=max_results)
            )

    async def _run_dorks(
        self, dorks: List[str], proxy: str, max_results: int = 10
    ) -> List[DiscoveryResult]:
        # The broader, unquoted fallback is intentionally narrower than the
        # primary query so a --max-results bump doesn't blow up the fallback
        # path just as much (it's already lower-confidence per hit).
        fallback_max = max(1, max_results // 2)
        results = []
        for query in dorks:
            # Exact, quoted dorks are higher-signal than the unquoted fallback.
            confidence = 0.7 if '"' in query else 0.55
            success = False
            for attempt in range(2):  # Limit attempts with same proxy
                try:
                    # Jitter to avoid rate-limiting, without blocking the loop.
                    await asyncio.sleep(random.uniform(3, 5))
                    kwargs = self._build_query_kwargs(proxy)
                    res = await asyncio.to_thread(
                        self._ddgs_text, kwargs, query, max_results
                    )
                    results.extend(self._rows_to_results(res, query, confidence))
                    # A clean (even empty) response means no transient error;
                    # stop retrying and let the fallback handle empties.
                    success = bool(res)
                    break
                except Exception as e:
                    logger.warning(
                        f"[x] Search attempt {attempt+1} failed for {query} with proxy {proxy}: {e}"
                    )
                    await asyncio.sleep(2 * (attempt + 1))

            if not success:
                # Exhaustive fallback: search without quotes if the query failed.
                try:
                    logger.info(f"[*] Falling back to broader query for {query}")
                    kwargs = self._build_query_kwargs(proxy)
                    res = await asyncio.to_thread(
                        self._ddgs_text, kwargs, query.replace('"', ""), fallback_max
                    )
                    results.extend(self._rows_to_results(res, query, 0.4))
                except Exception as e:
                    logger.warning(
                        f"[x] Search failed for {query} with proxy {proxy}: {e}"
                    )
        return self._dedupe(results)
