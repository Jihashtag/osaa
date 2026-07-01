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
from fusion_engine import FusionEngine

# The Probabilistic Identity Fusion Engine was implemented (and unit-tested in
# tests/test_fusion_engine.py) but never actually wired into the pipeline —
# every anchor was deduplicated by exact string match only. That let obvious
# variants of the same handle/email (case, punctuation, minor typos across
# tools) pile up as separate, unlinked anchors instead of being merged into
# one higher-confidence anchor, which is exactly the "not pertinent" noise in
# the final report.
_fusion_engine = FusionEngine()


def _merge_or_append(anchors: List[IdentityAnchor], res: DiscoveryResult) -> None:
    """Adds ``res.value`` as a new anchor, or — if it's a probable variant of
    an anchor already present — merges into that anchor instead."""
    existing = [a.value for a in anchors]
    if res.value in existing:
        return  # exact duplicate: nothing to add or merge

    best_anchor, best_prob = None, 0.0
    for anchor in anchors:
        prob = _fusion_engine.calculate_link_probability(
            res.value, anchor, res.source_tool
        )
        if _fusion_engine.is_link_valid(prob) and prob > best_prob:
            best_anchor, best_prob = anchor, prob

    if best_anchor is not None:
        best_anchor.aggregate_confidence = max(
            best_anchor.aggregate_confidence, res.confidence
        )
    else:
        anchors.append(
            IdentityAnchor(value=res.value, aggregate_confidence=res.confidence)
        )


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
            _merge_or_append(identity.email, res)
        elif res.target_type == "username":
            _merge_or_append(identity.username, res)
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
