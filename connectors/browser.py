import asyncio
import hashlib
import json
import os
import random
import requests

import undetected_chromedriver as uc

from logger import get_logger
from path_utils import get_report_dir

from time import sleep
from typing import List

from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from connectors.base import BaseConnector, DiscoveryResult
from utils.scraper import handle_captcha
from utils.url_filter import (
    is_search_engine_url,
    looks_like_serp,
    is_bot_block,
    registered_domain,
)

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")

NAVIGATE_TO = [
    "https://duckduckgo.com/?t=ffab&q=",
    "https://www.perplexity.ai/search/new?pc=chrome&q=",
    "https://www.bing.com/search?pc=MOZI&form=MOZLBR&q=",
    "https://www.google.com/search?sourceid=chrome&ie=UTF-8&q=",
    "https://yandex.com/search?search_source=yacom_desktop_common&text=",
]


def response_checker(perfLog: any) -> bool:
    response = None
    for logIndex in range(0, len(perfLog)):
        logMessage = json.loads(perfLog[logIndex]["message"])["message"]
        if logMessage["method"] == "Network.responseReceived":
            if logMessage["params"]["type"] == "Document":
                response = int(
                    logMessage["params"].get("response", {}).get("status", None)
                )

    if response is not None:
        if response < 200 or response >= 408 or response == 404:
            return False
        if response > 303:
            # It might be that we are blocked by bot control
            # 400 / 401 / 403 / 402? should be handled like by retrying with threshold ?
            # Or maybe an AI filling captcha ?
            # Or we use the screenshot to click / fill captcha ?
            # Or we simulate random mouse movement on every requests to make it "humany"
            # Or all of the above ... Anyway it's an improvement to try
            return False
    return True


class BrowserConnector(BaseConnector):
    def __init__(self):
        # Hard cap on page load so an unresponsive site cannot stall the run.
        self.page_load_timeout = int(os.getenv("BROWSER_PAGELOAD_TIMEOUT", "20"))

    @property
    def supported_types(self) -> List[str]:
        return ["url", "query", "username", "fullname"]

    def _setup_driver(self, proxy: str = None) -> webdriver.Chrome:
        options = uc.ChromeOptions()
        # Remove to fill captchas
        options.add_argument("--headless=new")
        options.add_argument("disable-infobars")
        options.add_argument("--no-sandbox")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        if proxy:
            if "https://" not in proxy:
                options.add_argument(f"--proxy-server={proxy}")
            else:
                options.add_argument(f"--proxy-server={proxy[8:]}")
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        driver = uc.Chrome(
            options=options,
            # user_data_dir="cookie_folder",
            keep_alive=False,
        )
        stealth(
            driver,
            languages=["en-US", "en", "fr-FR", "fr"],
            vendor="Google Inc.",
            platform="Win32",
            fix_hairline=True,
        )
        return driver

    def set_targets(self, targets):
        self.targets = set(
            {
                target["value"]
                for target in targets
                if "value" in target
                and target["value"] is not None
                and target["type"] in ["email", "username", "fullname"]
                and len(target["value"]) > 4
            }
        )

    def _handle_captcha(self, driver: webdriver.Chrome):
        """If a captcha is detected, try clicking submit buttons."""
        handle_captcha(driver)

    def _content_checker(self, driver: webdriver.Chrome) -> tuple | None:
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            content = body.text.lower()

            if is_bot_block(driver.current_url, content):
                logger.error(f"[x] Browser - {driver.current_url} was spotted")
                # We were spotted as a robot.
                # Todo : Retry with firefox and/or ipv4/ipv6
                self._handle_captcha(driver)
                sleep(random.uniform(3, 5))
                body = driver.find_element(By.TAG_NAME, "body")
                content = body.text.lower()
                if is_bot_block(driver.current_url, content):
                    return None
            # Reject search-engine result pages: the target string appears on
            # them by construction, but they are not evidence about the subject.
            if looks_like_serp(content):
                logger.debug(f"[x] Browser - {driver.current_url} looks like a SERP")
                return None
            if not any(
                target in content
                and "{target} not found" not in content
                and " a different user" not in content
                and "user not found" not in content
                and "profile not found" not in content
                for target in self.targets
                if target is not None
            ):
                return None
            content_hash = hashlib.md5(content.encode()).hexdigest()
            raw_path = os.path.join(self.res_dir, f"{content_hash}.raw")
        except Exception as e:
            logger.error(f"[x] Browser - {driver.current_url} - Body is invalid: {e}")
            return None

        if os.path.exists(raw_path):
            return None  # Deduplicated
        return (raw_path, content)

    def _capture_media(self, driver: webdriver.Chrome, raw_path: str) -> None:
        """Captures relevant media: Screenshots and profile pictures."""
        try:
            # Screenshot
            driver.save_screenshot(raw_path.replace(".raw", "_screen.png"))
        except Exception as e:
            logger.error(f"[x] BrowserConnector save screenshot from {raw_path}: {e}")
            pass

        images = None
        # Media assets (profile pictures, posts)
        try:
            images = driver.find_elements(By.TAG_NAME, "img")
        except:
            # No images where found
            return

        src = None
        for i, img in enumerate(images):
            try:
                # Ignore logos and such
                cls = img.get_attribute("class")
                ids = img.get_attribute("id")
                if "logo" in cls or "logo" in ids:
                    continue
            except:
                #  Image has no attribute class or id
                pass
            try:
                src = img.get_attribute("src")
            except:
                #  Image has no attribute src
                continue
            if src and src.startswith("http"):
                if "logo" in src or "brand" in src or "emblem" in src:
                    continue
                try:
                    ext = os.path.splitext(src.split("?")[0])[-1] or ".png"
                    if ext == ".svg":
                        continue
                    if len(ext) > 5:
                        ext = ".png"
                    img_path = f'{raw_path.replace(".raw", "_img")}_{i}{ext}'
                    with open(img_path, "wb") as f:
                        f.write(requests.get(src, timeout=5).content)
                except:
                    pass

    async def _navigate(self, driver):
        try:
            button = driver.find_elements(By.TAG_NAME, "button")
            for x in button:
                if "allow" in x.text.lower() or "accepter" in x.text.lower():
                    x.click()
                    await asyncio.sleep(random.uniform(3, 5))
        except:
            # If there are multiple one or none it might go wild
            pass
        try:
            a = driver.find_elements(By.TAG_NAME, "a")
            for x in a:
                if "allow" in x.text.lower() or "accepter" in x.text.lower():
                    x.click()
                    await asyncio.sleep(random.uniform(1, 2))
                    return
        except:
            # If there are none it might go wild
            pass
        try:
            # If we clicked on something this should fail, if not it will succeed
            len_click = len(button)
            for x in range(0, len_click):
                buttons = driver.find_elements(By.TAG_NAME, "button")
                button[x].click()
                await asyncio.sleep(random.uniform(0, 2))
        except:
            # We propably clicked already
            pass

    def _resolve_target(self, target_url: str, blocked_domains: set = None):
        """Resolve a raw target into a URL to visit, or None to skip.

        A bare token (username/name) is a *seed* search routed through an
        engine; a full URL is a *discovered result* (skipped if it is a SERP or
        on a domain that already bot-blocked us this run)."""
        is_seed = not target_url.startswith("http")
        if not is_seed and is_search_engine_url(target_url):
            logger.debug(f"[skip] SERP/engine URL not treated as evidence: {target_url}")
            return None
        if (
            not is_seed
            and blocked_domains is not None
            and registered_domain(target_url) in blocked_domains
        ):
            logger.debug(f"[skip] domain previously bot-blocked: {target_url}")
            return None
        if is_seed:
            target_url = random.choice(NAVIGATE_TO) + target_url
        return target_url

    async def _visit(
        self, driver, target_url: str, blocked_domains: set = None
    ) -> List[DiscoveryResult]:
        """Visit one already-resolved URL on an existing driver and return any
        evidence. Never raises for per-page issues (returns [])."""
        try:
            driver.set_page_load_timeout(self.page_load_timeout)
            driver.get(target_url)
        except TimeoutException:
            logger.error(f"[x] Browser - page load timed out: {target_url}")
            return []
        await asyncio.sleep(random.uniform(3, 5))

        # Detect bot-block interstitials (e.g. Google /sorry) and record the
        # domain so the rest of the run stops hammering it.
        if is_bot_block(driver.current_url):
            dom = registered_domain(driver.current_url)
            logger.warning(f"[x] Browser - bot-blocked on {dom}, backing off")
            if blocked_domains is not None and dom:
                blocked_domains.add(dom)
            return []

        await self._navigate(driver)

        perfLog = driver.get_log("performance")
        if not response_checker(perfLog):
            return []

        ret = self._content_checker(driver)
        if ret is None:
            return []

        raw_path, content = ret
        self._capture_media(driver, raw_path)
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"[✓] Browser - {target_url}")
        return [DiscoveryResult("browser", "url", target_url, {"raw_path": raw_path})]

    async def run(
        self,
        target_url: str,
        proxy: str = None,
        blocked_domains: set = None,
        **kwargs,
    ) -> List[DiscoveryResult]:
        """Visit a single target (thin wrapper around run_many)."""
        return await self.run_many([target_url], proxy=proxy, blocked_domains=blocked_domains)

    async def run_many(
        self,
        urls: List[str],
        proxy: str = None,
        blocked_domains: set = None,
    ) -> List[DiscoveryResult]:
        """Visit several URLs reusing ONE Chrome instance (launching+patching a
        fresh driver per URL was the dominant cost of a run)."""
        self.res_dir = get_report_dir()
        results: List[DiscoveryResult] = []
        # Don't pay a Chrome launch if every URL would be skipped (all SERPs /
        # all on blocked domains).
        if not any(self._resolve_target(u, blocked_domains) for u in urls):
            return []
        driver = None
        try:
            driver = self._setup_driver(proxy=proxy)
            if not driver:
                logger.error("[x] Browser could not init driver")
                return []
            for raw_url in urls:
                # Resolve lazily so a domain that bot-blocks us mid-batch is
                # skipped for its remaining URLs.
                resolved = self._resolve_target(raw_url, blocked_domains)
                if resolved is None:
                    continue
                try:
                    results.extend(await self._visit(driver, resolved, blocked_domains))
                except Exception as e:
                    logger.error(f"[x] Browser - {raw_url} : {e}")
        finally:
            if driver:
                try:
                    driver.close()
                    driver.quit()
                except Exception:
                    pass
        return results
