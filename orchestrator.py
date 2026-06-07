import gc
import os
import asyncio
from datetime import datetime

from logger import get_logger
from random import shuffle
from typing import Dict, List

from connectors.browser import BrowserConnector
from connectors.tor import TorConnector
from connectors.searcher import SearchConnector
from connectors.tookie import TookieConnector
from connectors.holehe import HoleheConnector
from connectors.holmes import HolmesConnector
from connectors.breach import BreachConnector
from identity_utils import update_identity_from_results
from models import MasterIdentity, Knowledge
from proxy_utils import check_proxy

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class Orchestrator:
    def __init__(self, proxies: List[str] = None, knowledge: Knowledge = None, ratio: float = 0.33):
        self.connectors = {
            "browser": BrowserConnector(),
            "tor": TorConnector(),
            "search": SearchConnector(),
            "tookie": TookieConnector(os.environ.get("TOOKIE_DIR", None)),
            "holehe": HoleheConnector(os.environ.get("HOLEHE_DIR", None)),
            "holmes": HolmesConnector(os.environ.get("HOLMES_DIR", None)),
            "breach": BreachConnector(),
        }
        self.identity = MasterIdentity()
        self.ratio = ratio
        self.knowledge = knowledge
        self.proxies = proxies or []
        self.working_proxies = []
        self.semaphore = asyncio.Semaphore(5)
        self.execution_log = []

    async def _run_with_semaphore(
        self, name: str, connector, target: str, proxies: List[str] = None, **kwargs
    ):
        """Runs a connector with semaphore to limit concurrency to 5."""
        async with self.semaphore:
            try:
                if name == "browser":
                    # Browser uses single 'proxy' parameter instead of proxies list
                    proxy = proxies[0] if proxies else None
                    result = await connector.run(target, proxy=proxy, **kwargs)
                else:
                    result = await connector.run(target, proxies=proxies, **kwargs)
                self.execution_log.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "tool": name,
                        "target": target,
                        "status": "success",
                        "artifacts_count": (
                            len(result) if isinstance(result, list) else 0
                        ),
                    }
                )
                return result
            except Exception as e:
                self.execution_log.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "tool": name,
                        "target": target,
                        "status": "error",
                        "error": str(e),
                    }
                )
                logger.error(f"[x] {name} on {target}: {e}")
                return []

    async def _update_working_proxies(self):
        """Checks which proxies are up."""
        if not self.proxies:
            self.working_proxies = []
            return

        logger.info(f"[*] Checking {len(self.proxies)} proxies...")
        # We can run checks in parallel
        checks = []
        for p in self.proxies:
            checks.append(asyncio.to_thread(check_proxy, p))

        results = await asyncio.gather(*checks)
        self.working_proxies = [p for p, is_up in zip(self.proxies, results) if is_up]
        logger.info(f"[*] {len(self.working_proxies)} working proxies found.")

    async def run_full_pipeline(
        self, targets: List[Dict[str, str]], knowledge: Knowledge = None
    ):
        if knowledge:
            self.knowledge = knowledge
        self.connectors["browser"].set_targets(targets)
        browser = self.connectors["browser"]
        i = 0
        len_target = len(targets)
        # Ensure we process at least the first targets if the list is small
        ratio = max(3, int(len_target * self.ratio))

        for target in targets:
            i += 1
            if i > 3:
                # Force garbage collection as we might skip it in some scenarios after the first 3
                gc.collect()
            # We want only the Original targets + most pertinent informations statistically -not all-
            if i > ratio:
                break
            t_type = target["type"]
            target_val = target["value"]
            if target_val is None or not target_val:
                continue

            tasks = []
            # 1. Connectors (Holehe/Tookie/Holmes)
            for name, connector in self.connectors.items():
                if name == "browser":
                    continue
                try:
                    if t_type in connector.supported_types:
                        if name == "search":
                            await self._update_working_proxies()
                        tasks.append(
                            self._run_with_semaphore(
                                name, connector, target_val, self.working_proxies
                            )
                        )
                except Exception as e:
                    logger.error(f"[x] {name} on {target_val}: {e}")
                    continue
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if not isinstance(res, list):
                    logger.error(f"[x] {target_val}: {res}")
                    continue
                # Gather usernames / emails / fullnames
                update_identity_from_results(self.identity, res)
                # Extend artifacts and url to scrap
                self.identity.raw_artifacts.extend(
                    r for r in res if r.target_type != "url"
                )
                self.identity.discovered_urls.extend(
                    r.value for r in res if r.target_type == "url"
                )

            # Force garabage collection as tools are used in way that might be unattended
            gc.collect()

            # 2. Browser
            urls = list(set(self.identity.discovered_urls))
            # TODO : Order by pertinence (similarities with default identity ?)
            shuffle(urls)
            ratio_browser = len(urls) * self.ratio

            if i > 3:
                urls = urls[: int(ratio_browser)]

            await self._update_working_proxies()
            if self.working_proxies:
                # Parallelize across proxies: sequential per proxy
                num_proxies = len(self.working_proxies)
                chunk_size = max(1, len(urls) // num_proxies)
                url_chunks = [
                    urls[i : i + chunk_size] for i in range(0, len(urls), chunk_size)
                ]

                async def _run_browser_chunk(chunk, proxy):
                    chunk_results = []
                    for url in chunk:
                        try:
                            res = await self._run_with_semaphore(
                                "browser",
                                browser,
                                url,
                                proxies=[proxy] if proxy else None,
                            )
                            chunk_results.extend(res)
                        except Exception as e:
                            logger.error(
                                f"Error on Browsing {url} with proxy {proxy}: {e}"
                            )
                    return chunk_results

                tasks = []
                for idx, chunk in enumerate(url_chunks):
                    proxy = self.working_proxies[idx % num_proxies]
                    tasks.append(_run_browser_chunk(chunk, proxy))

                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, list):
                        self.identity.raw_artifacts.extend(res)
                    elif isinstance(res, Exception):
                        logger.error(f"Error on Browser Task: {res}")
            else:
                for url in urls:
                    try:
                        res = await self._run_with_semaphore("browser", browser, url)
                        self.identity.raw_artifacts.extend(res)
                    except Exception as e:
                        logger.error(f"Error on Browsing {url} : {e}")
                        continue

            # We don't want to keep artifacts
            self.identity.discovered_urls.clear()
            # Force garbage collection as the browser (chrome) is sh*tty and used in unattended ways
            gc.collect()

        await self._update_working_proxies()
        # 3. Browser again but now search specifics usernames for additional informations
        usernames = list(set([a.value for a in self.identity.username]))
        if self.working_proxies:
            # Parallelize across proxies: sequential per proxy
            num_proxies = len(self.working_proxies)
            chunk_size = max(1, len(usernames) // num_proxies)
            user_chunks = [
                usernames[i : i + chunk_size]
                for i in range(0, len(usernames), chunk_size)
            ]

            async def _run_user_chunk(chunk, proxy):
                chunk_results = []
                for user in chunk:
                    try:
                        res = await self._run_with_semaphore(
                            "browser", browser, user, proxies=[proxy] if proxy else None
                        )
                        chunk_results.extend(res)
                    except Exception as e:
                        logger.error(
                            f"Error on Browsing user {user} with proxy {proxy}: {e}"
                        )
                return chunk_results

            tasks = []
            for idx, chunk in enumerate(user_chunks):
                proxy = self.working_proxies[idx % num_proxies]
                tasks.append(_run_user_chunk(chunk, proxy))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    self.identity.raw_artifacts.extend(res)
                elif isinstance(res, Exception):
                    logger.error(f"Error on Browser User Task: {res}")
        else:
            for username in usernames:
                try:
                    res = await self._run_with_semaphore("browser", browser, username)
                    self.identity.raw_artifacts.extend(res)
                except Exception as e:
                    logger.error(f"Error on Browsing user {username} : {e}")
                    continue
        # Force garbage collection as the browser (chrome) is sh*tty and used in unattended ways
        gc.collect()
