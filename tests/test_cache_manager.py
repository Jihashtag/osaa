import os
import tempfile
import unittest

from connectors.base import DiscoveryResult
from utils.cache import CacheManager


def _hit(value="v", confidence=1.0):
    return DiscoveryResult("holehe", "email", value, {"k": "v"}, confidence=confidence)


class TestCacheManagerInit(unittest.TestCase):
    def test_creates_missing_parent_directory(self):
        # Reproduces the CI failure: the target directory does not exist yet.
        base = tempfile.mkdtemp()
        db_path = os.path.join(base, "database", "fresh.sqlite")
        self.assertFalse(os.path.isdir(os.path.dirname(db_path)))
        manager = CacheManager(db_path=db_path)  # must not raise
        self.assertTrue(os.path.exists(manager.db_path))


class TestMakeKey(unittest.TestCase):
    def test_same_tool_and_target_produce_same_key(self):
        self.assertEqual(
            CacheManager.make_key("holehe", "a@b.com"),
            CacheManager.make_key("holehe", "A@B.com"),  # case-insensitive
        )

    def test_different_tool_or_target_produce_different_keys(self):
        k1 = CacheManager.make_key("holehe", "a@b.com")
        k2 = CacheManager.make_key("tookie", "a@b.com")
        k3 = CacheManager.make_key("holehe", "c@d.com")
        self.assertNotEqual(k1, k2)
        self.assertNotEqual(k1, k3)


class TestCacheManager(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_cache.sqlite"
        self.manager = CacheManager(db_name=self.db_name)

    def tearDown(self):
        if os.path.exists(self.manager.db_path):
            os.remove(self.manager.db_path)

    def test_miss_when_nothing_recorded(self):
        self.assertIsNone(self.manager.check_hit("nope"))

    def test_pertinent_result_is_a_permanent_hit(self):
        key = CacheManager.make_key("holehe", "a@b.com")
        self.manager.record_success(key, [_hit("twitter")], now=1_000_000)

        # Still a hit a full year later: pertinent results never expire.
        cached = self.manager.check_hit(key, now=1_000_000 + 365 * 86400)
        self.assertEqual(len(cached), 1)
        self.assertIsInstance(cached[0], DiscoveryResult)
        self.assertEqual(cached[0].value, "twitter")

    def test_negative_result_is_a_hit_within_ttl(self):
        key = CacheManager.make_key("holehe", "a@b.com")
        self.manager.record_success(key, [], now=1_000_000)

        # 1 hour later: still within the 1-day negative TTL -> hit (empty).
        self.assertEqual(self.manager.check_hit(key, now=1_000_000 + 3600), [])

    def test_negative_result_expires_after_ttl(self):
        key = CacheManager.make_key("holehe", "a@b.com")
        self.manager.record_success(key, [], now=1_000_000)

        # Just past the 1-day TTL -> miss, so the target gets rescanned.
        self.assertIsNone(
            self.manager.check_hit(key, now=1_000_000 + 24 * 3600 + 1)
        )

    def test_errors_are_never_recorded_so_always_a_miss(self):
        key = CacheManager.make_key("holehe", "a@b.com")
        # Simulates the caller's contract: an error must never call
        # record_success. There is nothing to record, so it's always a miss.
        self.assertIsNone(self.manager.check_hit(key))

    def test_invalidate_forces_a_miss(self):
        key = CacheManager.make_key("holehe", "a@b.com")
        self.manager.record_success(key, [_hit()], now=1_000_000)
        self.assertIsNotNone(self.manager.check_hit(key, now=1_000_000))
        self.manager.invalidate(key)
        self.assertIsNone(self.manager.check_hit(key, now=1_000_000))

    def test_re_recording_overwrites_previous_entry(self):
        key = CacheManager.make_key("holehe", "a@b.com")
        self.manager.record_success(key, [], now=1_000_000)
        self.manager.record_success(key, [_hit("found_now")], now=2_000_000)
        cached = self.manager.check_hit(key, now=2_000_000)
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0].value, "found_now")


if __name__ == "__main__":
    unittest.main()
