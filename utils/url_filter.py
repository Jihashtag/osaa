"""URL / SERP filtering helpers.

Pure functions (no Selenium, no network) shared by the browser connector, the
orchestrator and the report writer. They exist to keep search-engine result
pages (SERPs) and bot-block pages out of the evidence set, and to budget how
many URLs we visit per domain.
"""

from urllib.parse import urlparse
from typing import List

# Registered domains (and a few specific search subdomains) of engines we use as
# *seeds*. Pages served BY these hosts are search-result pages, never evidence.
SEARCH_ENGINE_DOMAINS = frozenset(
    {
        "google.com",
        "bing.com",
        "duckduckgo.com",
        "html.duckduckgo.com",
        "lite.duckduckgo.com",
        "yandex.com",
        "yandex.ru",
        "perplexity.ai",
        "brave.com",
        "search.brave.com",
        "mojeek.com",
        "startpage.com",
        "ecosia.org",
        "qwant.com",
        "baidu.com",
        "ask.com",
        "search.yahoo.com",
        "grokipedia.com",
        "en.wikipedia.org",  # opensearch API host seen in logs
    }
)

# Navigation/structure tokens that cluster on search-engine result pages.
_SERP_TOKENS = (
    "search results",
    "did you mean",
    "safe search",
    "safesearch",
    "images",
    "videos",
    "video",
    "maps",
    "settings",
    "all results",
    "web",
    "log in",
    "sign in",
)

_CAPTCHA_TOKENS = (
    "not a robot",
    "pas un robot",
    "verify you are",
    "verify you're",
    "unusual traffic",
    "captcha",
    "/sorry/",
)


def registered_domain(url: str) -> str:
    """Return the lowercased host of a URL with a leading ``www.`` removed.

    Returns ``""`` for empty/garbage input (never raises). Note: this is the
    host, not the eTLD+1 — we compare against an explicit allow/deny set rather
    than parsing public suffixes (no extra dependency)."""
    if not url or not isinstance(url, str):
        return ""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if not host:
        return ""
    host = host.split("@")[-1].split(":")[0]  # drop creds + port
    if host.startswith("www."):
        host = host[4:]
    return host


def is_search_engine_url(url: str) -> bool:
    """True if the URL is served by a known search engine (a SERP, not evidence)."""
    host = registered_domain(url)
    if not host:
        return False
    if host in SEARCH_ENGINE_DOMAINS:
        return True
    # Match subdomains of known engines (e.g. "www2.bing.com").
    return any(
        host == d or host.endswith("." + d) for d in SEARCH_ENGINE_DOMAINS
    )


def looks_like_serp(text: str) -> bool:
    """Heuristic: does this captured body text look like a search-results page?

    True when several distinct SERP navigation tokens co-occur. Tuned so a real
    profile page (few/none of these tokens) is not flagged."""
    if not text:
        return False
    low = text.lower()
    hits = sum(1 for tok in _SERP_TOKENS if tok in low)
    return hits >= 3


def is_bot_block(url: str, text: str = "") -> bool:
    """True if the page is a bot-block / captcha interstitial (e.g. Google /sorry)."""
    u = (url or "").lower()
    if "/sorry/" in u:
        return True
    low = (text or "").lower()
    return any(tok in low for tok in _CAPTCHA_TOKENS)


def cap_per_domain(urls: List[str], n: int = 5) -> List[str]:
    """Keep at most ``n`` URLs per registered domain, preserving input order.

    The default of 5 is deliberately generous (commandment: maximise results)
    while still bounding the per-domain crawl cost."""
    counts: dict = {}
    out: List[str] = []
    for u in urls:
        dom = registered_domain(u) or u
        if counts.get(dom, 0) >= n:
            continue
        counts[dom] = counts.get(dom, 0) + 1
        out.append(u)
    return out
