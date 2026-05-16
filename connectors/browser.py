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

from connectors.base import BaseConnector, DiscoveryResult

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")

NAVIGATE_TO = [
    "https://duckduckgo.com/?t=ffab&q=",
    "https://www.perplexity.ai/search/new?pc=chrome&q=",
    "https://www.bing.com/search?pc=MOZI&form=MOZLBR&q=",
    "https://www.google.com/search?sourceid=chrome&ie=UTF-8&q=",
    "https://yandex.com/searchi?search_source=yacom_desktop_common&text=",
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
        pass

    @property
    def supported_types(self) -> List[str]:
        return ["url", "query", "username", "fullname"]

    def _setup_driver(self, proxy: str = None) -> webdriver.Chrome:
        options = uc.ChromeOptions()
        # Remove to fill captchas
        options.add_argument("--headless=new")
        options.add_argument("disable-infobars")
        options.add_argument("--no-sandbox")
        if proxy:
            options.add_argument(f"--proxy-server={proxy}")
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        driver = uc.Chrome(options=options, version_main=147)
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
        try:
            submits = driver.find_elements(By.XPATH, "//input[@type='submit']")
            for submit in submits:
                logger.info()
                submit.click()
                sleep(random.uniform(2, 4))
        except Exception as e:
            logger.error(f"[x] Browser - Error handling captcha: {e}")

    def _content_checker(self, driver: webdriver.Chrome) -> tuple | None:
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            content = body.text.lower()

            if " not a robot" in content or " pas un robot" in content:
                logger.error(f"[x] Browser - {driver.current_url} was spotted")
                # We were spotted as a robot.
                # Todo : Retry with firefox and/or ipv4/ipv6
                self._handle_captcha(driver)
                sleep(random.uniform(3, 5))
                body = driver.find_element(By.TAG_NAME, "body")
                content = body.text.lower()
                if " not a robot" in content or " pas un robot" in content:
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

    def _navigate(self, driver):
        try:
            button = driver.find_elements(webdriver.common.by.By.TAG_NAME, "button")
            for x in button:
                if "allow" in x.text.lower() or "accepter" in x.text.lower():
                    x.click()
                    sleep(random.uniform(3, 5))
        except:
            # If there are multiple one or none it might go wild
            pass
        try:
            a = driver.find_elements(webdriver.common.by.By.TAG_NAME, "a")
            for x in a:
                if "allow" in x.text.lower() or "accepter" in x.text.lower():
                    x.click()
                    sleep(random.uniform(1, 2))
                    return
        except:
            # If there are none it might go wild
            pass
        try:
            # If we clicked on something this should fail, if not it will succeed
            len_click = len(button)
            for x in range(0, len_click):
                buttons = driver.find_elements(
                    webdriver.common.by.By.TAG_NAME, "button"
                )
                button[x].click()
                sleep(random.uniform(0, 2))
        except:
            # We propably clicked already
            pass

    async def run(self, target_url: str, proxy: str = None) -> List[DiscoveryResult]:
        self.res_dir = get_report_dir()

        if not target_url.startswith("http"):
            target_url = random.choice(NAVIGATE_TO) + target_url

        driver = None
        try:
            driver = self._setup_driver(proxy=proxy)
            if not driver:
                logger.error("[x] Browser could not init driver")
                return
            driver.get(target_url)
            sleep(random.uniform(3, 5))

            self._navigate(driver)

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

            driver.close()
            logger.info(f"[✓] Browser - {target_url}")
            return [
                DiscoveryResult("browser", "url", target_url, {"raw_path": raw_path})
            ]
        except Exception as e:
            if driver:
                driver.close()
            logger.error(f"[x] Browser - {target_url} : {e}")
            return []
        finally:
            if driver:
                driver.quit()
