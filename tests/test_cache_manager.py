import os
import tempfile
import unittest
from utils.cache import CacheManager


class TestCacheManagerInit(unittest.TestCase):
    def test_creates_missing_parent_directory(self):
        # Reproduces the CI failure: the target directory does not exist yet.
        base = tempfile.mkdtemp()
        db_path = os.path.join(base, "database", "fresh.sqlite")
        self.assertFalse(os.path.isdir(os.path.dirname(db_path)))
        manager = CacheManager(db_path=db_path)  # must not raise
        self.assertTrue(os.path.exists(manager.db_path))
        manager.record_discovery("h", {"ok": 1})
        self.assertEqual(manager.check_hit("h"), {"ok": 1})


class TestCacheManager(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_cache.sqlite"
        self.manager = CacheManager(db_name=self.db_name)

    def tearDown(self):
        if os.path.exists(self.manager.db_path):
            os.remove(self.manager.db_path)

    def test_cache_cycle(self):
        test_hash = "abcdef123456"
        test_data = {"result": "hit"}

        # Check miss
        self.assertIsNone(self.manager.check_hit(test_hash))

        # Record
        self.manager.record_discovery(test_hash, test_data)

        # Check hit
        hit = self.manager.check_hit(test_hash)
        self.assertEqual(hit, test_data)


if __name__ == "__main__":
    unittest.main()
