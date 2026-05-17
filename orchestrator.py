import gc
import os
import asyncio

from logger import get_logger
from random import shuffle
from typing import Dict, List

from connectors.browser import BrowserConnector
from connectors.tor import TorConnector
from connectors.searcher import SearchConnector
from connectors.tookie import TookieConnector
from connectors.holehe import HoleheConnector
from connectors.holmes import HolmesConnector
from identity_utils import update_identity_from_results
from models import MasterIdentity
from proxy_utils import check_proxy

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class Orchestrator:
    def __init__(self, proxies: List[str] = None):
        self.connectors = {
            "browser": BrowserConnector(),
            "tor": TorConnector(),
            "search": SearchConnector(),
            "tookie": TookieConnector(os.environ.get("TOOKIE_DIR", None)),
            "holehe": HoleheConnector(os.environ.get("HOLEHE_DIR", None)),
            "holmes": HolmesConnector(os.environ.get("HOLMES_DIR", None)),
        }
        self.identity = MasterIdentity()
        self.proxies = proxies or []
        self.working_proxies = []

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

    async def run_full_pipeline(self, targets: List[Dict[str, str]]):
        self.connectors["browser"].set_targets(targets)
        browser = self.connectors["browser"]
        i = 0
        len_target = len(targets)
        # Ensure we process at least the first targets if the list is small
        ratio = max(3, int(len_target * 0.33))

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
                            connector.run(target_val, proxies=self.working_proxies)
                        )
                except Exception as e:
                    logger.error(f"[x] {name} on {target_val}: {e}")
                    continue
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
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
            shuffle(urls)
            ratio_browser = len(urls) * 0.33

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
                            res = await browser.run(url, proxy=proxy)
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
                        res = await browser.run(url)
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
        usernames = list(set(self.identity.username))
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
                        res = await browser.run(user, proxy=proxy)
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
                    res = await browser.run(username)
                    self.identity.raw_artifacts.extend(res)
                except Exception as e:
                    logger.error(f"Error on Browsing user {username} : {e}")
                    continue
        # Force garbage collection as the browser (chrome) is sh*tty and used in unattended ways
        gc.collect()
