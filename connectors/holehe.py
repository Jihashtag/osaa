from logger import get_logger
import os

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")
import subprocess
import json
import os
from typing import List
from connectors.base import BaseConnector, DiscoveryResult


class HoleheConnector(BaseConnector):
    """Connector for the holehe OSINT tool."""

    def __init__(self, holehe_dir: str = None):
        if holehe_dir is None:
            BASE_DIR = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.holehe_dir = os.path.join(BASE_DIR, "docker_holehe")
        else:
            self.holehe_dir = holehe_dir

    @property
    def supported_types(self) -> List[str]:
        return ["email"]

    async def run(self, target: str, **kwargs) -> List[DiscoveryResult]:
        # Holehe uses a docker container.
        cmd = ["holele", target, "--no-color"]

        # Using run_in_executor to keep the loop non-blocking
        import asyncio

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: subprocess.run(cmd, capture_output=True, text=True)
        )

        results = []
        try:
            output_lines = result.stdout.splitlines()
            for line in output_lines:
                try:
                    if not line.startswith("[+]"):
                        continue
                    results.append(
                        DiscoveryResult(
                            source_tool="holehe",
                            target_type="email",
                            value=f"{target} is used on : {line[4:]}",
                            metadata={"used": True, "title": line},
                        )
                    )
                    logger.info(f"[✓] holehe: {target}")
                except json.JSONDecodeError as e:
                    logger.info(f"[x] holehe: {target} - Error {e}")
                    continue
        except Exception as e:
            logger.info(f"[x] holehe: {target} - Error")
            logger.info(f"Error parsing holehe output: {e}")

        return results
