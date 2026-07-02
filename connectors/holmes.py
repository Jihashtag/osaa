import asyncio
import json
import os
import sys
import time

from time import sleep
from typing import List
from unittest.mock import patch, MagicMock

from connectors.base import BaseConnector, DiscoveryResult
from logger import get_logger
from path_utils import get_report_dir
from proxy_utils import load_proxies, get_working_proxies

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class MockTranslation:
    @staticmethod
    def Get_Language():
        return "Lang/english.json"

    @staticmethod
    def Translate_Language(filename, List, Row, SubRow=None):
        ret = None
        try:
            with open(filename, "r") as f:
                ret = json.loads(f.read())
        except:
            pass
        try:
            return ret[List][0][Row][SubRow]
        except:
            return ret[List][Row]

    @staticmethod
    def Get_Language2():
        return "ENGLISH"


class HolmesConnector(BaseConnector):

    # Re-validate the holmes proxy pool at most once per this window, and never
    # check more than this many proxies (the bundled list has hundreds of mostly
    # dead entries, each costing a network round-trip).
    PROXY_CACHE_TTL = 86400  # 24h
    MAX_PROXY_CHECK = 30
    PROXY_CHECK_TIMEOUT = 3  # seconds

    def __init__(self, holmes_dir: str = None):
        if holmes_dir is None:
            BASE_DIR = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.holmes_dir = os.path.join(BASE_DIR, "python_holmes")
        else:
            self.holmes_dir = holmes_dir
        sys.path.append(self.holmes_dir)
        # Proxy filtering performs network I/O, so it must NOT run in the
        # constructor (that blocked/leaked on every Orchestrator() and made the
        # whole test suite hit the live internet). It is done lazily, once, on
        # the first run() call where we are guaranteed an async context.
        self._proxies_filtered = False

    async def _filter_proxies(self):
        """Validates the holmes proxy pool and writes the working subset.

        Runs once; subsequent calls are no-ops. Safe to await from run()."""
        if self._proxies_filtered:
            return
        self._proxies_filtered = True

        proxy_all = os.path.join(self.holmes_dir, "Proxies", "Proxy_list_all.txt")
        proxy_out = os.path.join(self.holmes_dir, "Proxies", "Proxy_list.txt")

        if not os.path.exists(proxy_all):
            return

        # Disk cache: if a recently-written working list exists, reuse it.
        if os.path.exists(proxy_out):
            age = time.time() - os.path.getmtime(proxy_out)
            if age < self.PROXY_CACHE_TTL:
                logger.info("holmes: using cached working proxies (within TTL)")
                return

        try:
            with open(proxy_all, "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
            proxies = proxies[: self.MAX_PROXY_CHECK]

            working = await get_working_proxies(
                proxies, timeout=self.PROXY_CHECK_TIMEOUT
            )
            logger.info(f"Working proxies: {working}")
            if not any(working):
                working = await get_working_proxies(
                    load_proxies(), timeout=self.PROXY_CHECK_TIMEOUT
                )

            with open(proxy_out, "w") as f:
                for p in working:
                    f.write(f"{p}\n")
        except Exception as e:
            logger.error(f"[x] holmes proxy filtering failed: {e}")

    @property
    def supported_types(self) -> List[str]:
        return ["email", "username", "fullname"]

    def _run_holmes_emails(self, target):
        if not os.path.exists(self.holmes_dir):
            raise Exception(f"Invalid dir for holmes: {self.holmes_dir}")

        # We use path_utils.get_report_dir which anchors to original CWD
        report_dir = get_report_dir(target)
        report_path = os.path.join(
            self.holmes_dir, f"GUI/Reports/E-Mail/{target}/{target}.txt"
        )

        original_dir = os.getcwd()
        try:
            os.chdir(self.holmes_dir)

            if not os.path.exists("Configuration/Configuration.ini"):
                # Not configured — "could not even attempt this", not
                # "attempted and found nothing". Raise so the caller treats
                # it as an error to retry, instead of caching an empty
                # result for a day.
                raise RuntimeError(
                    "holmes not configured (Configuration/Configuration.ini missing)"
                )

            with patch("builtins.input", return_value="2"), patch(
                "Core.Support.Mail.Mail_Validator.Validator.Mail", return_value=True
            ), patch("Core.Support.Language.Translation", new=MockTranslation), patch(
                "Core.Support.Banner_Selector.Random.Get_Banner", return_value=None
            ), patch(
                "Core.Support.Notification.Notifier.Start", return_value=None
            ):
                from Core.E_Mail import Mail_search

                Mail_search.Search(target, "default")

            results = []
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    results.append(
                        DiscoveryResult("holmes", "email", target, {"content": content})
                    )
                os.rename(report_path, f"{report_dir}/email_{target}_python_holmes.txt")
                logger.info(f"[✓] holmes: {target}")
            else:
                logger.info(f"[!] holmes: {target}: Report not found")
            return results
        finally:
            os.chdir(original_dir)

    def _run_holmes_person(self, target):
        if not os.path.exists(self.holmes_dir):
            raise Exception(f"Invalid dir for holmes: {self.holmes_dir}")

        # We use path_utils.get_report_dir which anchors to original CWD
        report_dir = get_report_dir(target)
        target_slug = target.replace(" ", "_")
        report_path = os.path.join(
            self.holmes_dir, f"GUI/Reports/People/{target_slug}/{target_slug}.txt"
        )
        final_report_path = f"{report_dir}/user_{target_slug}_python_holmes.txt"

        # Check if already exists
        if os.path.exists(final_report_path):
            logger.info(f"[*] holmes: using existing report for {target}")
            with open(final_report_path, "r", encoding="utf-8") as f:
                return [
                    DiscoveryResult("holmes", "username", target, {"content": f.read()})
                ]

        original_dir = os.getcwd()
        try:
            os.chdir(self.holmes_dir)

            if not os.path.exists("Configuration/Configuration.ini"):
                # See _run_holmes_emails: raise rather than swallow, so this
                # is retried next run instead of cached as a negative result.
                raise RuntimeError(
                    "holmes not configured (Configuration/Configuration.ini missing)"
                )

            with patch("builtins.input", return_value="1"), patch(
                "Core.Support.Mail.Mail_Validator.Validator.Mail", return_value=True
            ), patch("Core.Support.Creds.Sender.mail", return_value=None), patch(
                "Core.Support.Language.Translation", new=MockTranslation
            ), patch(
                "builtins.print", new=logger.info
            ), patch(
                "Core.Support.Encoding.Encoder.Encode", return_value=None
            ), patch(
                "Core.Support.FileTransfer.Transfer.File", return_value=None
            ), patch(
                "Core.Support.Clear.Screen.Clear", return_value=None
            ), patch(
                "Core.Support.Banner_Selector.Random.Get_Banner", return_value=None
            ), patch(
                "Core.Support.Notification.Notifier.Start", return_value=None
            ):
                from Core.Searcher_person import info

                info.Banner = lambda x: print(x)
                info.Search(target, "default")

            results = []
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    results.append(
                        DiscoveryResult(
                            "holmes", "username", target, {"content": content}
                        )
                    )
                os.makedirs(report_dir, exist_ok=True)
                os.rename(report_path, final_report_path)
                logger.info(f"[✓] holmes: {target}")
            else:
                logger.info(f"[!] holmes: {target_slug}: Report not found")

            # Get generated dorks
            if os.path.exists(
                f"{self.holmes_dir}/GUI/Reports/People/Dorks/{target_slug}_Dorks.txt"
            ):
                with open(
                    f"{self.holmes_dir}/GUI/Reports/People/Dorks/{target_slug}_Dorks.txt",
                    "r",
                ) as f:
                    ret = f.readlines()
                    for line in ret:
                        if line.startswith("| http"):
                            # Strip the "| " table prefix to recover the URL.
                            # The URL is the result *value*; the originating
                            # target goes in metadata for traceability.
                            url = line[2:].strip()
                            results.append(
                                DiscoveryResult(
                                    "holmes", "url", url, {"query": target}
                                )
                            )
            else:
                logger.info(f"[!] holmes: {target_slug}: Dorks not found")
            return results
        finally:
            os.chdir(original_dir)

    async def run(self, target: str, **kwargs) -> List[DiscoveryResult]:
        loop = asyncio.get_running_loop()
        await self._filter_proxies()

        # Deliberately no try/except here: a genuine failure (unconfigured
        # tool, unexpected exception) should propagate to the Orchestrator,
        # which logs it and — importantly — does NOT cache it, so it's
        # retried next run instead of being treated as "scanned, no hits".
        if "@" in target:
            return await loop.run_in_executor(None, self._run_holmes_emails, target)
        else:
            return await loop.run_in_executor(None, self._run_holmes_person, target)
