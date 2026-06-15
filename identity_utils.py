import hashlib
import binascii

from random import randbytes
from typing import List, Any


def sha256_hex(val: str) -> str:
    """Returns the SHA256 hex digest of a string, lowercased."""
    return hashlib.sha256(val.strip().lower().encode("utf-8")).hexdigest()


from connectors.base import DiscoveryResult
from path_utils import get_report_dir
from models import IdentityAnchor
from blocklist import is_local_noise


def update_identity_from_results(identity, results: List[DiscoveryResult]):
    """
    Populates MasterIdentity from discovery results.
    Maps tool-specific output to standard model fields.
    """
    if not results or not isinstance(results, list) or not any(results):
        return
    for res in results:
        if not res:
            continue
        # Drop artifacts that are really local project noise (tool names,
        # source paths) before they enter the identity graph.
        if res.value and is_local_noise(res.value):
            continue
        if res.target_type == "email":
            existing = [a.value for a in identity.email]
            if res.value not in existing:
                identity.email.append(
                    IdentityAnchor(value=res.value, aggregate_confidence=res.confidence)
                )
        elif res.target_type == "username":
            existing = [a.value for a in identity.username]
            if res.value not in existing:
                identity.username.append(
                    IdentityAnchor(value=res.value, aggregate_confidence=res.confidence)
                )
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
