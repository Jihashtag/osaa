import os
from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz
from models import MasterIdentity, IdentityAnchor
from connectors.base import DiscoveryResult
from utils.config import load_reliability_weights
from logger import get_logger

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class FusionEngine:
    """
    Probabilistic Identity Fusion Engine (PIFE).
    Implements linking logic based on similarity and source trust.
    """

    def __init__(self):
        self.weights = load_reliability_weights()

    def _get_fuzz_score(self, a: str, b: str) -> float:
        """Calculates normalized fuzzy similarity [0-1]."""
        return fuzz.token_set_ratio(a, b) / 100.0

    def _get_domain_bonus(self, a: str, b: str) -> float:
        """Adds a bonus if both artifacts share a high-signal domain (e.g. ProtonMail)."""
        high_signal_domains = [
            "proton.me",
            "protonmail.com",
            "tutanota.com",
            "duck.com",
        ]
        if "@" in a and "@" in b:
            dom_a = a.split("@")[1].lower()
            dom_b = b.split("@")[1].lower()
            if dom_a == dom_b and dom_a in high_signal_domains:
                return 0.1
        return 0.0

    def calculate_link_probability(
        self, new_artifact: str, existing_anchor: IdentityAnchor, source_tool: str
    ) -> float:
        """
        Equation: P = (FuzzScore * 0.6) + (SourceTrust * 0.3) + (ContextBonus * 0.1)
        """
        fuzz_score = self._get_fuzz_score(new_artifact, existing_anchor.value)
        source_trust = self.weights.get(source_tool, 0.5)
        context_bonus = self._get_domain_bonus(new_artifact, existing_anchor.value)

        prob = (fuzz_score * 0.6) + (source_trust * 0.3) + (context_bonus * 0.1)
        return min(1.0, prob)

    def is_link_valid(self, prob: float, threshold: float = 0.80) -> bool:
        """Determines if a link should be established based on threshold."""
        if 0.6 <= prob < threshold:
            logger.warning(
                f"[!] POTENTIAL LINK DETECTED (P={prob:.2f}). Requires manual review."
            )
        return prob >= threshold
