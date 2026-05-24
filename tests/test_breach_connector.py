import unittest
import asyncio
from connectors.breach import BreachConnector


class TestBreachConnector(unittest.TestCase):
    def setUp(self):
        self.connector = BreachConnector()

    def test_hashing_requirement(self):
        self.assertTrue(self.connector.requires_hashing)

    def test_run_hit(self):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(self.connector.run("test@example.com"))
        self.assertEqual(len(results), 1)
        self.assertIn("breach_connector", results[0].source_tool)

    def test_run_miss(self):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(self.connector.run("unknown@example.com"))
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
