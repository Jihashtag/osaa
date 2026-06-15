"""Edge-case coverage for knowledge_loader and the reliability-config loader."""

import unittest
from unittest.mock import patch

from knowledge_loader import KnowledgeLoader
from models import Knowledge
from utils.config import load_reliability_weights


class TestKnowledgeLoaderEdges(unittest.TestCase):
    def test_from_dict_filters_unknown_and_none_keys(self):
        k = KnowledgeLoader.from_dict(
            {"email": "a@b.com", "username": None, "bogus": "x"}
        )
        self.assertEqual(k.identity, {"email": "a@b.com"})
        self.assertEqual(k.behavioral_tags, [])

    def test_from_dict_preserves_tags_and_metadata(self):
        k = KnowledgeLoader.from_dict(
            {"username": "u", "behavioral_tags": ["t"], "metadata": {"s": "cli"}}
        )
        self.assertIsInstance(k, Knowledge)
        self.assertEqual(k.behavioral_tags, ["t"])
        self.assertEqual(k.metadata, {"s": "cli"})


class TestConfigLoaderFallback(unittest.TestCase):
    def test_falls_back_to_defaults_when_file_missing(self):
        with patch("utils.config.os.path.exists", return_value=False):
            weights = load_reliability_weights()
        # Defaults must include the core tools and be sane probabilities.
        self.assertIn("holehe", weights)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in weights.values()))

    def test_loads_real_config_file(self):
        weights = load_reliability_weights()
        self.assertIsInstance(weights, dict)
        self.assertTrue(weights)


if __name__ == "__main__":
    unittest.main()
