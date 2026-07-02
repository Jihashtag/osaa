import gc
import os
import asyncio
import time
from datetime import datetime

from logger import get_logger
from typing import Any, Dict, List

from connectors.browser import BrowserConnector
from connectors.tor import TorConnector
from connectors.searcher import SearchConnector
from connectors.tookie import TookieConnector
from connectors.holehe import HoleheConnector
from connectors.holmes import HolmesConnector
from connectors.breach import BreachConnector
from identity_utils import update_identity_from_results
from identity_expander import IdentityExpander
from models import MasterIdentity, Knowledge
from proxy_utils import check_proxy
from utils.cache import CacheManager
from utils.config import load_reliability_weights
from utils.url_filter import cap_per_domain, is_search_engine_url

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class Orchestrator:
    def __init__(
        self,
        proxies: List[str] = None,
        knowledge: Knowledge = None,
        ratio: float = 0.33,
        tookie_dir: str = None,
        holmes_dir: str = None,
        max_results: int = 10,
        max_pages: int = 5,
        breach_api_key: str = None,
        breach_backend: str = "auto",
        use_cache: bool = False,
        cache: "CacheManager" = None,
    ):
        self.connectors = {
            "browser": BrowserConnector(),
            "tor": TorConnector(),
            "search": SearchConnector(),
            "tookie": TookieConnector(tookie_dir or os.environ.get("TOOKIE_DIR")),
            # holehe shells out to the CLI on PATH; there is no directory to pass.
            "holehe": HoleheConnector(),
            "holmes": HolmesConnector(holmes_dir or os.environ.get("HOLMES_DIR")),
            "breach": BreachConnector(
                breach_api_key or os.environ.get("HIBP_API_KEY"),
                backend=breach_backend,
            ),
        }
        # Per-(tool, target) discovery cache — see utils/cache.py for the hit
        # policy. Defaults OFF here (opt-in via use_cache/cache) so a bare
        # Orchestrator() — as used throughout the test suite — never touches
        # the real on-disk cache; main.py turns it on by default for real
        # CLI runs (--no-cache to disable).
        self.cache = cache if cache is not None else (CacheManager() if use_cache else None)
        self.identity = MasterIdentity()
        self.ratio = ratio
        self.knowledge = knowledge
        self.proxies = proxies or []
        self.working_proxies = []
        self.semaphore = asyncio.Semaphore(5)
        self.execution_log = []
        # Proxy validation is expensive (one network round-trip per proxy) and
        # was previously repeated on every dispatch. Cache the result and only
        # re-validate after this TTL elapses.
        self._proxy_check_ttl = 300  # seconds
        self._proxy_last_checked = 0.0
        # Domains that bot-blocked us this run; the browser backs off from them.
        self._blocked_domains: set = set()
        # --max-results: how many hits the SearchConnector asks DDGS for per
        # dork query.
        self.max_results = max_results
        # --max-pages: how many pages get crawled per domain by the browser,
        # and how many onion search engines the Tor connector visits per
        # target (generous default: maximise results).
        self.max_pages = max_pages
        # source_tool reliability weights, used to rank discovered URLs so a
        # ratio-based cap drops the *weakest* candidates instead of a random
        # sample of them (see _score_url).
        self._source_weights = load_reliability_weights() or {}
        # Best (confidence, source reliability) seen per URL this run.
        self._url_scores: Dict[str, float] = {}

    async def _run_with_semaphore(
        self, name: str, connector, target: str, proxies: List[str] = None, **kwargs
    ):
        """Runs a connector with semaphore to limit concurrency to 5.

        Checks the discovery cache first — a hit skips the network call and
        the semaphore entirely — and only records *successful* fetches, never
        errors, so a failed attempt (connector exception, proxy down, ...) is
        retried on the next run instead of being mistaken for "already
        scanned, found nothing". See utils/cache.py for the exact hit policy.
        """
        cache_key = self.cache.make_key(name, target) if self.cache else None
        if cache_key is not None:
            cached = self.cache.check_hit(cache_key)
            if cached is not None:
                # print(), not logger.info(): this is exactly the kind of
                # thing a user asks "is the cache actually being used?"
                # about, so it shouldn't be hidden behind --debug.
                print(
                    f"[cache] {name} on {target}: reusing {len(cached)} cached "
                    "artifact(s), no re-fetch"
                )
                self.execution_log.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "tool": name,
                        "target": target,
                        "status": "cache_hit",
                        "artifacts_count": len(cached),
                    }
                )
                return cached

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
                if cache_key is not None and isinstance(result, list):
                    # A caching failure (e.g. a malformed/non-serializable
                    # result) must never turn a real, successful fetch into
                    # a reported error and discard its data — isolate it.
                    try:
                        self.cache.record_success(cache_key, result)
                    except Exception as cache_err:
                        logger.error(
                            f"[x] cache write failed for {name} on {target}: {cache_err}"
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
                # Not cached on purpose — see the docstring above.
                return []

    def plan(self, targets: List[Dict[str, str]]) -> List[Dict]:
        """Return the execution plan (which connectors would run per target)
        without performing any network I/O. Backs ``osaa plan``."""
        plan = []
        for target in targets:
            t_type = target.get("type")
            val = target.get("value")
            if not val:
                continue
            names = [
                name
                for name, connector in self.connectors.items()
                if name != "browser" and t_type in connector.supported_types
            ]
            plan.append({"type": t_type, "value": val, "connectors": names})
        return plan

    def _connector_kwargs(self, name: str) -> Dict[str, Any]:
        """Extra per-connector kwargs derived from --max-results/--max-pages."""
        if name == "search":
            return {"max_results": self.max_results}
        if name == "tor":
            return {"max_pages": self.max_pages}
        return {}

    async def _browse_urls(self, browser, urls: List[str]) -> List:
        """Browse a set of URLs, reusing one Chrome per proxy chunk (or one for
        the whole set when there are no proxies). Returns collected artifacts."""
        if not urls:
            return []
        artifacts: List = []

        async def _chunk(chunk, proxy=None):
            async with self.semaphore:
                try:
                    return await browser.run_many(
                        chunk,
                        proxy=proxy,
                        blocked_domains=self._blocked_domains,
                    )
                except Exception as e:
                    logger.error(f"Error on Browser chunk (proxy={proxy}): {e}")
                    return []

        if self.working_proxies:
            num = len(self.working_proxies)
            size = max(1, len(urls) // num)
            chunks = [urls[i : i + size] for i in range(0, len(urls), size)]
            tasks = [
                _chunk(chunk, self.working_proxies[idx % num])
                for idx, chunk in enumerate(chunks)
            ]
            for res in await asyncio.gather(*tasks, return_exceptions=True):
                if isinstance(res, list):
                    artifacts.extend(res)
                elif isinstance(res, Exception):
                    logger.error(f"Error on Browser Task: {res}")
        else:
            artifacts.extend(await _chunk(urls))
        return artifacts

    async def _run_speculative_account_checks(self):
        """When the subject has a username but no known email, derive candidate
        emails and run the email-capable connectors (holehe/breach) on them so a
        username-only investigation still yields account-existence signal.

        Results are tagged ``speculative`` and confidence-capped so they never
        outrank confirmed findings (commandment 1: maximise results, safely)."""
        if self.identity.email:
            return  # a real email is known; no need to guess
        usernames = list({a.value for a in self.identity.username if a})
        if not usernames:
            return

        candidates = []
        for user in usernames[:3]:
            candidates.extend(IdentityExpander.derive_candidate_emails(user))
        candidates = list(dict.fromkeys(candidates))  # dedupe, keep order

        tasks = []
        for email in candidates:
            for name in ("holehe", "breach"):
                connector = self.connectors[name]
                if "email" in connector.supported_types:
                    tasks.append(
                        self._run_with_semaphore(
                            name, connector, email, self.working_proxies
                        )
                    )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if not isinstance(res, list):
                continue
            for r in res:
                meta = getattr(r, "metadata", None)
                if isinstance(meta, dict):
                    meta["speculative"] = True
                if hasattr(r, "confidence"):
                    r.confidence = min(float(r.confidence or 1.0), 0.5)
            update_identity_from_results(self.identity, res)
            self.identity.raw_artifacts.extend(
                r for r in res if r.target_type != "url"
            )

    async def _update_working_proxies(self, force: bool = False):
        """Checks which proxies are up, caching the result for a TTL window."""
        if not self.proxies:
            self.working_proxies = []
            return

        now = time.monotonic()
        if (
            not force
            and self.working_proxies
            and (now - self._proxy_last_checked) < self._proxy_check_ttl
        ):
            # Recent successful check still valid; skip the network round-trips.
            return

        logger.info(f"[*] Checking {len(self.proxies)} proxies...")
        # We can run checks in parallel
        checks = []
        for p in self.proxies:
            checks.append(asyncio.to_thread(check_proxy, p))

        results = await asyncio.gather(*checks)
        self.working_proxies = [p for p, is_up in zip(self.proxies, results) if is_up]
        self._proxy_last_checked = time.monotonic()
        logger.info(f"[*] {len(self.working_proxies)} working proxies found.")

    def _record_url_score(self, url: str, confidence: float, source_tool: str) -> None:
        """Tracks the best (confidence * source-reliability) score seen for a
        URL this run, so it can be ranked instead of randomly sampled when the
        ratio cap forces us to drop candidates."""
        score = float(confidence or 1.0) * self._source_weights.get(source_tool, 0.5)
        if score > self._url_scores.get(url, -1.0):
            self._url_scores[url] = score

    async def run_full_pipeline(
        self, targets: List[Dict[str, str]], knowledge: Knowledge = None
    ):
        if knowledge:
            self.knowledge = knowledge
        self._blocked_domains = set()  # fresh per run
        self._url_scores = {}
        self.connectors["browser"].set_targets(targets)
        browser = self.connectors["browser"]
        i = 0
        len_target = len(targets)
        # Ensure we process at least the first targets if the list is small
        ratio = max(3, int(len_target * self.ratio))
        print(
            f"[*] Discovery: {len_target} target(s) queued, processing the top "
            f"{min(ratio, len_target)} (ratio={self.ratio})"
        )

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
                                name,
                                connector,
                                target_val,
                                self.working_proxies,
                                **self._connector_kwargs(name),
                            )
                        )
                except Exception as e:
                    logger.error(f"[x] {name} on {target_val}: {e}")
                    continue
            print(
                f"[*] ({i}/{min(ratio, len_target)}) {t_type}:{target_val} — "
                f"dispatching {len(tasks)} connector(s)"
            )
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
                for r in res:
                    if r.target_type == "url":
                        self.identity.discovered_urls.append(r.value)
                        self._record_url_score(r.value, r.confidence, r.source_tool)

            # Force garabage collection as tools are used in way that might be unattended
            gc.collect()

            # 2. Browser
            urls = list(set(self.identity.discovered_urls))
            # Drop search-engine result pages (not evidence) and bound the crawl
            # to a few URLs per domain so one domain can't dominate the budget.
            urls = [u for u in urls if not is_search_engine_url(u)]
            urls = cap_per_domain(urls, n=self.max_pages)
            # Best evidence first: a ratio cap below then drops the *weakest*
            # candidates instead of a random sample of them (previously
            # shuffle()'d, which could just as easily discard the best hits).
            urls.sort(key=lambda u: self._url_scores.get(u, 0.5), reverse=True)
            ratio_browser = len(urls) * self.ratio

            if i > 3:
                urls = urls[: int(ratio_browser)]

            if urls:
                print(f"[*]   browsing {len(urls)} discovered URL(s)...")
            await self._update_working_proxies()
            self.identity.raw_artifacts.extend(await self._browse_urls(browser, urls))

            # We don't want to keep artifacts
            self.identity.discovered_urls.clear()
            # Force garbage collection as the browser (chrome) is sh*tty and used in unattended ways
            gc.collect()

        # 2.5 Speculative account-existence checks on usernames lacking an email.
        print("[*] Speculative account checks on username-only identities...")
        await self._run_speculative_account_checks()

        await self._update_working_proxies()
        # 3. Browser again but now search specific usernames for additional info.
        usernames = list(set([a.value for a in self.identity.username]))
        print(f"[*] Final pass: browsing {len(usernames)} known username(s)...")
        self.identity.raw_artifacts.extend(await self._browse_urls(browser, usernames))
        # Force garbage collection as the browser (chrome) is sh*tty and used in unattended ways
        gc.collect()
        self._print_cache_summary()
        print("[*] Discovery pipeline complete.")

    def _print_cache_summary(self) -> None:
        """Prints a one-line breakdown of connector dispatches this run —
        how many were served from cache vs. actually fetched vs. errored —
        so the discovery cache's effect is visible without inspecting the
        sqlite file directly."""
        if self.cache is None:
            print("[*] Cache: disabled (--no-cache)")
            return
        counts = {"cache_hit": 0, "success": 0, "error": 0}
        for entry in self.execution_log:
            status = entry.get("status")
            if status in counts:
                counts[status] += 1
        total = sum(counts.values())
        if total == 0:
            return
        print(
            f"[*] Cache: {counts['cache_hit']}/{total} dispatch(es) served from "
            f"cache, {counts['success']} fetched live, {counts['error']} errored"
        )
