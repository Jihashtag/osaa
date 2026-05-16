import unittest
from connectors.searcher import SearchConnector
from profiles import Profiles
import asyncio


class TestSearchConnector(unittest.IsolatedAsyncioTestCase):
    async def test_search(self):
        connector = SearchConnector()
        results = await connector.run("John Lambert")
        self.assertGreaterEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
