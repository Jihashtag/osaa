from logger import get_logger
import os

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")
import subprocess
import os
from typing import List
from connectors.base import BaseConnector, DiscoveryResult


class HoleheConnector(BaseConnector):
    """Connector for the holehe OSINT tool.

    Shells out to the ``holehe`` console script installed on PATH (pip
    package), not a checkout on disk — there is no directory to configure."""

    @property
    def supported_types(self) -> List[str]:
        return ["email"]

    async def run(self, target: str, **kwargs) -> List[DiscoveryResult]:
        # Holehe uses a docker container.
        cmd = ["holehe", target, "--no-color"]

        # Using run_in_executor to keep the loop non-blocking
        import asyncio

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120
                ),
            )
        except FileNotFoundError:
            logger.error("[x] holehe: binary not found on PATH")
            return []
        except subprocess.TimeoutExpired:
            logger.error(f"[x] holehe: timed out for {target}")
            return []

        results = []
        try:
            output_lines = result.stdout.splitlines()
            for line in output_lines:
                # holehe emits plain text; "[+] <service>" marks a hit.
                if not line.startswith("[+]"):
                    continue
                service = line[4:].strip()
                # Use target_type="account" (not "email"): the value is a
                # service name, not an email address. Tagging it as "email"
                # would pollute MasterIdentity.email anchors and corrupt fusion.
                results.append(
                    DiscoveryResult(
                        source_tool="holehe",
                        target_type="account",
                        value=service,
                        metadata={"used": True, "email": target, "service": service},
                    )
                )
                logger.info(f"[✓] holehe: {target} -> {service}")
        except Exception as e:
            logger.info(f"[x] holehe: {target} - Error parsing holehe output: {e}")

        return results
