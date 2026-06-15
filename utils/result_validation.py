"""Validation for raw search results (pure, no I/O).

Some engines (notably the Tor onion search front-ends) echo the query back on an
otherwise-empty page. Such pages match a naive ``query in content`` test but are
not evidence. ``is_meaningful_result`` rejects bare echoes.
"""

from typing import List, Optional


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def is_meaningful_result(
    query: str, content: str, links: Optional[List[str]] = None, *, min_extra: int = 40
) -> bool:
    """True if ``content`` is a substantive result for ``query``.

    A result counts when the query appears AND either there are outbound links,
    or there is meaningful text beyond the bare query (``min_extra`` chars).
    A page that merely echoes the query returns False."""
    q = _norm(query)
    c = _norm(content)
    if not q or not c:
        return False
    if q not in c:
        return False
    if links:
        return True
    extra = c.replace(q, "").strip()
    return len(extra) >= min_extra
