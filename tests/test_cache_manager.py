import unittest
import os
from utils.cache import CacheManager


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
