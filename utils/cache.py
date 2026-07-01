import hashlib
import json
import os
import sqlite3
import time
from dataclasses import asdict
from typing import List, Optional

from connectors.base import DiscoveryResult


class CacheManager:
    """
    SQLite-backed cache of per-(tool, target) discovery results, keyed so a
    target already scanned by a given connector isn't re-scanned needlessly.

    Policy:
      - A fetch that found pertinent (non-empty) results is cached
        indefinitely: any later lookup for the same (tool, target) is a hit
        and is served straight from the cache — no re-fetch, no duplicate
        artifacts.
      - A fetch that legitimately found nothing is cached as a negative
        result for ``negative_ttl`` seconds (default 1 day). A lookup inside
        that window is a hit (empty list, no re-fetch); once it expires, the
        next lookup is a miss so the target gets a fresh chance.
      - A fetch that errored (connector exception, proxy down, timeout, ...)
        must NOT be recorded here at all — callers should only call
        ``record_success`` for fetches that actually completed. That keeps
        every subsequent lookup a miss, so a failed attempt is retried on the
        very next run instead of being mistaken for "already scanned".
    """

    NEGATIVE_TTL = 24 * 60 * 60  # 1 day, in seconds

    def __init__(
        self,
        db_name: str = "cache.sqlite",
        db_path: str = None,
        negative_ttl: float = None,
    ):
        if db_path:
            self.db_path = db_path
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(base_dir, "database", db_name)
        # The "database/" directory is not tracked by git (git can't store empty
        # dirs), so a fresh checkout (CI) won't have it. Create it on demand;
        # otherwise sqlite3.connect raises "unable to open database file".
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.negative_ttl = (
            self.NEGATIVE_TTL if negative_ttl is None else negative_ttl
        )
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discovery_cache (
                    hash TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    is_empty INTEGER NOT NULL,
                    fetched_at REAL NOT NULL
                )
                """
            )

    @staticmethod
    def make_key(source_tool: str, target_value: str) -> str:
        """Deterministic cache key for a (tool, target) pair."""
        raw = f"{source_tool}:{target_value}".strip().lower()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def check_hit(self, key: str, now: float = None) -> Optional[List[DiscoveryResult]]:
        """Returns the cached ``DiscoveryResult`` list if ``key`` is still a
        valid hit, or ``None`` if the caller must (re-)fetch it.

        There is deliberately no entry at all for a target whose last fetch
        errored — see the class docstring — so those are always a miss."""
        now = time.time() if now is None else now
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data, is_empty, fetched_at FROM discovery_cache WHERE hash = ?",
                (key,),
            )
            row = cursor.fetchone()
        if not row:
            return None
        data, is_empty, fetched_at = row
        if is_empty and (now - fetched_at) >= self.negative_ttl:
            return None  # negative result expired; give the target another chance
        return [DiscoveryResult(**d) for d in json.loads(data)]

    def record_success(
        self, key: str, results: List[DiscoveryResult], now: float = None
    ) -> None:
        """Records a fetch that *completed* (pertinent or legitimately
        empty). Never call this for a fetch that errored."""
        now = time.time() if now is None else now
        payload = [asdict(r) for r in results]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO discovery_cache (hash, data, is_empty, fetched_at) "
                "VALUES (?, ?, ?, ?)",
                (key, json.dumps(payload), 1 if not results else 0, now),
            )

    def invalidate(self, key: str) -> None:
        """Forces the next lookup for ``key`` to be a miss."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM discovery_cache WHERE hash = ?", (key,))
