import sqlite3
import os
import json
from typing import Optional, Any


class CacheManager:
    """
    Manages SQLite-based caching for OSINT artifacts.
    """

    def __init__(self, db_name: str = "cache.sqlite"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "database", db_name)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discovery_cache (
                    hash TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def check_hit(self, target_hash: str) -> Optional[Any]:
        """Checks if a hash is in the cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM discovery_cache WHERE hash = ?", (target_hash,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return None

    def record_discovery(self, target_hash: str, data: Any):
        """Records a discovery result in the cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO discovery_cache (hash, data) VALUES (?, ?)",
                (target_hash, json.dumps(data)),
            )
