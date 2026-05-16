from random import randbytes
from typing import List, Any

from connectors.base import DiscoveryResult
from path_utils import get_report_dir


def update_identity_from_results(identity, results: List[DiscoveryResult]):
    """
    Populates MasterIdentity from discovery results.
    Maps tool-specific output to standard model fields.
    """
    if not results or not any(results):
        return
    for res in results:
        if not res:
            continue
        if res.target_type == "email":
            if res.value not in identity.email:
                identity.email.append(res.value)
        elif res.target_type == "username":
            if res.value not in identity.username:
                identity.username.append(res.value)
        elif res.target_type in ["url", "query"]:
            if res.value not in identity.discovered_urls:
                identity.discovered_urls.append(res.value)

        report_path = get_report_dir()
        filename = None
        if res.target_type != "url" and res.value is not None:
            filename = f"{res.source_tool}_{res.target_type}_{binascii.hexlify(randbytes(5)).decode()}.raw"
            with open(
                f"{report_path}/{filename}",
                "w+",
            ) as output:
                output.write(f"======REPORT======\n\n{res.value}")
