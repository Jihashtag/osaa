import json
import os
import subprocess

from connectors.base import BaseConnector, DiscoveryResult
from logger import get_logger
from typing import List

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class TookieConnector(BaseConnector):

    def __init__(self, tookie_dir: str = None):
        if tookie_dir is None:
            BASE_DIR = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.tookie_dir = os.path.join(BASE_DIR, "python_tookie")
        else:
            self.tookie_dir = tookie_dir

    @property
    def supported_types(self) -> List[str]:
        return ["username", "fullname", "email"]

    async def run(self, target: str, **kwargs) -> List[DiscoveryResult]:
        cmd = [
            "python3",
            "brib.py",
            "-sk",
            "-a",
            "-t",
            "20",
            "-u",
            target,
            "-o",
            "json",
        ]

        try:
            subprocess.run(cmd, cwd=self.tookie_dir, capture_output=True, text=True)
            output_file = os.path.join(self.tookie_dir, f"{target}.json")
            if os.path.exists(output_file):
                with open(output_file, "r") as fd:
                    data = json.loads(fd.read())
                    results = []
                    for entry in data:
                        if entry.get("found", False) or entry.get("status", 0) in [
                            200,
                            403,
                        ]:
                            title = str(entry.get("url", target))
                            results.append(
                                DiscoveryResult(
                                    "tookie",
                                    "url",
                                    entry.get("url", target),
                                    {"title": title},
                                )
                            )
                        # Trigger async verification via BrowserConnector here would be complex due to loop handling.
                        # Simplified: Ensure it returns metadata to let the orchestrator run a follow-up Browser crawl.
                    logger.info(f"[✓] tookie: {target}")
                    return results
            logger.info(f"[x] tookie: {target}: didn't generate output")
            return []
        except Exception as e:
            logger.info(f"[x] tookie: {target}: {e}")
            return []
