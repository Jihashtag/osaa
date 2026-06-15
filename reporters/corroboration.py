"""Corroborate certified-knowledge facts against the collected OSINT evidence.

Pure (no I/O). For each biographical knowledge fact, report whether the OSINT
text supports it (``corroborated``), supports it in part (``partial``) or not at
all (``unconfirmed``). This lets the report separate *what we were told* from
*what we actually found* instead of merely restating the input knowledge.

Limitation: matching is token-based (with light fuzzy tolerance) and
language-agnostic only insofar as the surface tokens match — it will not bridge
translations (e.g. "medical" vs French "médecine").
"""

import re
from typing import Any, Dict, List

from rapidfuzz import fuzz

# Identity keys that are search *seeds*, not facts to corroborate.
_SEED_KEYS = {"email", "username"}


def _tokens(s: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) >= 3]


def _identity_of(knowledge: Any) -> Dict[str, Any]:
    identity = getattr(knowledge, "identity", None)
    if identity is None and isinstance(knowledge, dict):
        identity = knowledge.get("identity", {})
    return identity or {}


def assess(
    knowledge: Any, artifact_texts: List[str], *, token_threshold: int = 88
) -> List[Dict[str, str]]:
    """Return one row per biographical knowledge fact with a corroboration
    status and the matched tokens as evidence."""
    text_tokens = set()
    for t in artifact_texts or []:
        text_tokens.update(_tokens(t))

    rows: List[Dict[str, str]] = []
    for key, value in _identity_of(knowledge).items():
        if key in _SEED_KEYS or not isinstance(value, str) or not value.strip():
            continue
        vtoks = _tokens(value)
        matched = [
            vt
            for vt in vtoks
            if vt in text_tokens
            or any(fuzz.ratio(vt, tt) >= token_threshold for tt in text_tokens)
        ]
        if vtoks and len(matched) == len(vtoks):
            status = "corroborated"
        elif matched:
            status = "partial"
        else:
            status = "unconfirmed"
        rows.append(
            {
                "fact": key,
                "value": value,
                "status": status,
                "evidence": ", ".join(matched),
            }
        )
    return rows
