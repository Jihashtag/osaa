import asyncio
import os
import random
import subprocess
import hashlib
from time import sleep
from typing import List

import undetected_chromedriver as uc
from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from logger import get_logger
from utils.scraper import handle_captcha
from connectors.base import BaseConnector, DiscoveryResult

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")

ENGINE_LINKS = [
    "https://onion.live/?category=search%20engine",
    "http://5n4qdkw2wavc55peppyrelmb2rgsx7ohcb2tkxhub2gyfurxulfyd3id.onion/index.php?cat=Search",
]


class TorConnector(BaseConnector):
    def __init__(self):
        self.res_dir = None
        self.targets = set()

    @property
    def supported_types(self) -> List[str]:
        return ["username", "fullname", "email"]

    def _is_tor_running(self) -> bool:
        """Checks if the tor daemon is running using pgrep."""
        try:
            subprocess.check_output(["pgrep", "tor"])
            return True
        except subprocess.CalledProcessError:
            return False
        except Exception as e:
            logger.error(f"[!] Tor ecountered: {e}")
            return False

    def _setup_driver(self) -> webdriver.Chrome:
        options = uc.ChromeOptions()
        # Remove to fill captchas
        options.add_argument("--headless=new")
        options.add_argument("disable-infobars")
        options.add_argument("--no-sandbox")
        # Set proxy to Tor SOCKS5 proxy
        options.add_argument("--proxy-server=socks5://127.0.0.1:9050")
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        driver = uc.Chrome(options=options)
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            fix_hairline=True,
        )
        return driver

    def _handle_captcha(self, driver: webdriver.Chrome):
        """If a captcha is detected, try clicking submit buttons."""
        handle_captcha(driver)

    async def _search_engine_discovery(self, driver: webdriver.Chrome) -> List[str]:
        """Finds onion search engines from onion.live."""
        engines = []
        for discovery_link in ENGINE_LINKS:
            try:
                driver.get(discovery_link)
                await asyncio.sleep(random.uniform(1, 3))
                # Extract links that look like onion links or go to search engine pages
                links = driver.find_elements(By.TAG_NAME, "span")
                for link in links:
                    try:
                        if link.get_attribute("class") not in [
                            "single-mirror-text",
                            "link-onion",
                        ]:
                            continue
                    except:
                        continue
                    href = link.text
                    if href and ".onion" in href:
                        engines.append(href)
                logger.info(f"[*] Tor - Discovered {len(engines)} onion search engines")
            except Exception as e:
                logger.error(f"[x] Tor - Error discovering engines: {e}")
        # Filter and deduplicate
        engines = list(set(engines))
        return engines

    async def run(self, target: str, **kwargs) -> List[DiscoveryResult]:
        from path_utils import get_report_dir

        self.res_dir = get_report_dir()

        if not self._is_tor_running():
            logger.warn("[!] Tor - Daemon not found, skipping Tor connector.")
            return []

        results = []
        driver = None
        try:
            driver = self._setup_driver()
            if not driver:
                logger.error("[x] Tor could not init driver")
                return

            # Step 1: Discovery from onion.live
            engines = await self._search_engine_discovery(driver)

            # Step 2: Search on each engine
            for engine_url in engines[:3]:  # Limit to first 3 to avoid infinite loop
                try:
                    logger.info(f"[*] Tor - Searching on {engine_url}")
                    driver.get(engine_url)
                    await asyncio.sleep(random.uniform(2, 3))

                    # Try to find search input
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    search_box = None
                    for i in inputs:
                        if i.get_attribute("type") in [
                            "text",
                            "search",
                        ] or i.get_attribute("name") in ["q", "search", "query"]:
                            search_box = i
                            break

                    self._handle_captcha(driver)

                    if search_box:
                        search_box.send_keys(target)
                        search_box.send_keys(Keys.RETURN)
                    else:
                        # try with most common format
                        driver.get(f"{engine_url}/search?q={target}")

                    await asyncio.sleep(random.uniform(1, 3))
                    # Handle captcha if needed
                    self._handle_captcha(driver)

                    # Check content
                    content = driver.find_element(By.TAG_NAME, "body").text
                    if target.lower() in content.lower():
                        content_hash = hashlib.md5(content.encode()).hexdigest()
                        raw_path = os.path.join(self.res_dir, f"tor_{content_hash}.raw")
                        with open(raw_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        driver.save_screenshot(raw_path.replace(".raw", "_screen.png"))

                        results.append(
                            DiscoveryResult(
                                source_tool=f"tor_{engine_url}",
                                target_type="search",
                                value=target,
                                metadata={"raw_path": raw_path},
                            )
                        )
                        logger.info(
                            f"[✓] Tor - Success searching on {engine_url}: {target}"
                        )
                    else:
                        logger.info(
                            f"[!] Tor - No results on {engine_url} for : {target}"
                        )

                    # Navigate back using driver.back()
                    driver.back()
                    await asyncio.sleep(random.uniform(2, 4))
                except Exception as e:
                    logger.error(f"[x] Tor - Error searching on {engine_url}: {e}")
                    continue

            # Step 3: Search on DuckDuckGo and Yandex via Tor
            for engine in [
                "https://duckduckgo.com/?q=",
                "https://yandex.com/search/?text=",
            ]:
                try:
                    url = engine + target
                    logger.info(f"[*] Tor - Searching on {url}")
                    driver.get(url)
                    await asyncio.sleep(random.uniform(1, 3))
                    self._handle_captcha(driver)

                    content = driver.find_element(By.TAG_NAME, "body").text
                    if target.lower() in content.lower():
                        content_hash = hashlib.md5(content.encode()).hexdigest()
                        raw_path = os.path.join(
                            self.res_dir, f"tor_global_{content_hash}.raw"
                        )
                        with open(raw_path, "w", encoding="utf-8") as f:
                            f.write(content)
                        driver.save_screenshot(raw_path.replace(".raw", "_screen.png"))
                        results.append(
                            DiscoveryResult(
                                source_tool="tor_global",
                                target_type="search",
                                value=target,
                                metadata={"raw_path": raw_path},
                            )
                        )
                        logger.info(
                            f"[✓] Tor - Success searching on {engine}: {target}"
                        )
                except Exception as e:
                    logger.error(f"[x] Tor - Error searching on {engine}: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"[x] Tor - Major error: {e}")
            return results
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
