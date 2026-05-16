from dataclasses import dataclass
from typing import Optional


@dataclass
class DiscoveryProfile:
    """Strategy for tool execution, defining user behavior and anonymity."""

    user_agent: str
    proxy: Optional[str] = None
    delay_factor: float = 1.0
    mode: str = "default"  # e.g., 'fast', 'stealth', 'browser'


class Profiles:
    BOT = DiscoveryProfile(
        user_agent="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        mode="fast",
    )
    FIREFOX = DiscoveryProfile(
        user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
        mode="browser",
    )
    BING = DiscoveryProfile(
        user_agent="Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        mode="fast",
    )
