"""E3.5 — holmes proxy filtering uses a disk cache (no repeat network)."""

import os
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

from connectors.holmes import HolmesConnector


def _holmes_dir_with_proxies():
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "Proxies"))
    with open(os.path.join(d, "Proxies", "Proxy_list_all.txt"), "w") as f:
        f.write("1.2.3.4:80\n5.6.7.8:81\n")
    return d


class TestHolmesProxyCache(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_cache_skips_network(self):
        d = _holmes_dir_with_proxies()
        with patch(
            "connectors.holmes.get_working_proxies",
            new_callable=AsyncMock,
            return_value=["1.2.3.4:80"],
        ) as m:
            await HolmesConnector(holmes_dir=d)._filter_proxies()
            self.assertEqual(m.call_count, 1)  # validated once, wrote cache
            # a fresh instance within TTL must reuse the cache, not re-validate
            await HolmesConnector(holmes_dir=d)._filter_proxies()
            self.assertEqual(m.call_count, 1)
        self.assertTrue(os.path.exists(os.path.join(d, "Proxies", "Proxy_list.txt")))

    async def test_caps_number_of_proxies_validated(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "Proxies"))
        with open(os.path.join(d, "Proxies", "Proxy_list_all.txt"), "w") as f:
            f.write("\n".join(f"10.0.0.{i}:80" for i in range(200)))
        with patch(
            "connectors.holmes.get_working_proxies",
            new_callable=AsyncMock,
            return_value=[],
        ) as m:
            c = HolmesConnector(holmes_dir=d)
            c.MAX_PROXY_CHECK = 30
            await c._filter_proxies()
            # first positional arg is the (capped) proxy list
            checked = m.call_args[0][0]
            self.assertLessEqual(len(checked), 30)


if __name__ == "__main__":
    unittest.main()
