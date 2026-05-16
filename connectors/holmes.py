import asyncio
import json
import os
import sys

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

    def __init__(self, holmes_dir: str = None):
        if holmes_dir is None:
            BASE_DIR = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.holmes_dir = os.path.join(BASE_DIR, "python_holmes")
        else:
            self.holmes_dir = holmes_dir
        sys.path.append(self.holmes_dir)
        self._filter_proxies()

    def _filter_proxies(self):
        proxy_all = os.path.join(self.holmes_dir, "Proxies", "Proxy_list_all.txt")
        proxy_out = os.path.join(self.holmes_dir, "Proxies", "Proxy_list.txt")

        if not os.path.exists(proxy_all):
            return

        async def run_filtering():
            with open(proxy_all, "r") as f:
                proxies = [line.strip() for line in f if line.strip()]

            working = await get_working_proxies(proxies)
            logger.info(f"Working proxies: {working}")
            if not any(working):
                working = await get_working_proxies(load_proxies())

            with open(proxy_out, "w") as f:
                for p in working:
                    f.write(f"{p}\n")

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(run_filtering())
            else:
                loop.run_until_complete(run_filtering())
        except:
            pass

    @property
    def supported_types(self) -> List[str]:
        return ["email", "username", "fullname"]

    def _run_holmes_emails(self, target):
        if not os.path.exists(self.holmes_dir):
            raise Exception(f"Invalid dir for holmes: {self.holmes_dir}")

        # We use path_utils.get_report_dir which anchors to original CWD
        report_dir = get_report_dir(target)
        report_path = os.path.join(report_dir, f"{target}_report.txt")

        original_dir = os.getcwd()
        try:
            os.chdir(self.holmes_dir)

            if not os.path.exists("Configuration/Configuration.ini"):
                os.chdir(original_dir)
                return []

            with patch("builtins.input", return_value="2"), patch(
                "Core.Support.Mail.Mail_Validator.Validator.Mail", return_value=True
            ), patch("Core.Support.Language.Translation", new=MockTranslation), patch(
                "Core.Support.Banner_Selector.Random.Get_Banner", return_value=None
            ), patch(
                "Core.Support.Notification.Notifier.Start", return_value=None
            ):
                from Core.E_Mail import Mail_search

                Mail_search.searcher(target, report_path, "default")

            results = []
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    results.append(
                        DiscoveryResult("holmes", "email", target, {"content": content})
                    )
                os.rename(report_path, f"{report_dir}/email_{target}_python_holmes.txt")
            logger.info(f"[✓] holmes: {target}")
            os.chdir(original_dir)
            return results

        except Exception as e:
            logger.error(f"[x] holmes: {target}: {e}")
            os.chdir(original_dir)
            return []

    def _run_holmes_person(self, target):
        if not os.path.exists(self.holmes_dir):
            raise Exception(f"Invalid dir for holmes: {self.holmes_dir}")

        # We use path_utils.get_report_dir which anchors to original CWD
        report_dir = get_report_dir(target)
        target_slug = target.replace(" ", "_")
        report_path = f"GUI/Reports/People/{target_slug}/{target_slug}.txt"
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
                os.chdir(original_dir)
                return []

            with patch("builtins.input", return_value="1"), patch(
                "Core.Support.Mail.Mail_Validator.Validator.Mail", return_value=True
            ), patch("Core.Support.Creds.Sender.mail", return_value=None), patch(
                "Core.Support.Language.Translation", new=MockTranslation
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
            os.chdir(original_dir)
            return results

        except Exception as e:
            logger.error(f"[x] holmes: {target}: {e}")
            os.chdir(original_dir)
            return []

    async def run(self, target: str, **kwargs) -> List[DiscoveryResult]:
        loop = asyncio.get_running_loop()

        try:
            if "@" in target:
                return await loop.run_in_executor(None, self._run_holmes_emails, target)
            else:
                return await loop.run_in_executor(None, self._run_holmes_person, target)
        except Exception as e:
            logger.error(f"[x] holmes root: {target}: {e}")
            return []
