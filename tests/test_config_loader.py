import unittest
from utils.config import load_reliability_weights


class TestConfigLoader(unittest.TestCase):
    def test_load_weights(self):
        weights = load_reliability_weights()
        self.assertIn("holehe", weights)
        self.assertEqual(weights["holehe"], 0.95)
        self.assertIn("searcher", weights)
        self.assertEqual(weights["searcher"], 0.55)


if __name__ == "__main__":
    unittest.main()
