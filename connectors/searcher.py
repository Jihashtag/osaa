import asyncio
import os
import random

from time import sleep
from ddgs import DDGS
from logger import get_logger
from connectors.base import BaseConnector, DiscoveryResult
from typing import List

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class SearchConnector(BaseConnector):
    # Tiered Dorks: Start specific, broaden if no results

    @property
    def supported_types(self) -> List[str]:
        return ["query", "username", "email", "fullname"]

    async def run(
        self, target: str, proxies: List[str] = None, **kwargs
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
            return await self._run_dorks(dorks, None)

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
            tasks.append(self._run_dorks(chunk, proxy))

        results = await asyncio.gather(*tasks)
        # Flatten results
        return [item for sublist in results for item in sublist]

    async def _run_dorks(self, dorks: List[str], proxy: str) -> List[DiscoveryResult]:
        results = []
        for query in dorks:
            success = False
            for attempt in range(2):  # Limit attempts with same proxy
                try:
                    kwargs = {"verify": False}
                    if proxy is not None:
                        kwargs["proxy"] = proxy if "https://" not in proxy else proxy[8:]
                    with DDGS(**kwargs) as ddgs:
                        sleep(random.uniform(3, 5))
                        res = list(ddgs.text(
                            query,
                            safesearch="off",
                            max_results=10,
                        ))
                        for r in res:
                            results.append(
                                DiscoveryResult(
                                    "searcher",
                                    "url",
                                    r["href"],
                                    {
                                        "title": r["title"],
                                        "snippet": r["body"],
                                        "query": query,
                                    },
                                )
                            )
                        if res:
                            success = True
                            break
                        else:
                            # If no error but no results, maybe query is bad?
                            # Continue to fallback
                            break
                except Exception as e:
                    logger.warning(
                        f"[x] Search attempt {attempt+1} failed for {query} with proxy {proxy}: {e}"
                    )
                    sleep(2 * (attempt + 1))

            if not success:
                # Exhaustive fallback: Search without quotes if query fails
                try:
                    logger.info(f"[*] Falling back to broader query for {query}")
                    with DDGS(proxy=proxy, verify=False) as ddgs:
                        res = list(ddgs.text(query.replace('"', ""), max_results=5))
                        for r in res:
                            results.append(
                                DiscoveryResult(
                                    "searcher",
                                    "url",
                                    r["href"],
                                    {"title": r["title"], "snippet": r["body"]},
                                )
                            )
                except Exception as e:
                    logger.warning(
                        f"[x] Search failed for {query} with proxy {proxy}: {e}"
                    )
                    pass
        return results
