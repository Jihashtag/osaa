import unittest
import json
import os
from knowledge_loader import KnowledgeLoader
from models import Knowledge


class TestKnowledgeFromText(unittest.TestCase):
    def test_from_text_carries_notes_and_identity(self):
        k = KnowledgeLoader.from_text(
            "french medical student in Lille", username="lolla_lamb15", email=None
        )
        self.assertIsInstance(k, Knowledge)
        self.assertEqual(k.identity, {"username": "lolla_lamb15"})
        self.assertEqual(k.metadata["notes"], "french medical student in Lille")
        # to_dict must include the notes so the analyst sees them
        self.assertIn("notes", k.to_dict()["metadata"])

    def test_from_text_empty_is_safe(self):
        k = KnowledgeLoader.from_text("", username="u")
        self.assertEqual(k.metadata, {})
        self.assertEqual(k.identity, {"username": "u"})


class TestKnowledgeLoader(unittest.TestCase):
    def setUp(self):
        self.test_json_path = "test_knowledge.json"
        self.sample_data = {
            "identity": {"email": "test@example.com", "fullname": "Test User"},
            "behavioral_tags": ["active", "developer"],
            "metadata": {"source": "manual"},
        }
        with open(self.test_json_path, "w") as f:
            json.dump(self.sample_data, f)

    def tearDown(self):
        if os.path.exists(self.test_json_path):
            os.remove(self.test_json_path)

    def test_from_json(self):
        knowledge = KnowledgeLoader.from_json(self.test_json_path)
        self.assertIsInstance(knowledge, Knowledge)
        self.assertEqual(knowledge.identity["email"], "test@example.com")
        self.assertEqual(knowledge.behavioral_tags, ["active", "developer"])

    def test_from_dict(self):
        # Simulating CLI args as a dict
        args_dict = {
            "email": "cli@example.com",
            "fullname": "CLI User",
            "username": "cliuser",
        }
        knowledge = KnowledgeLoader.from_dict(args_dict)
        self.assertIsInstance(knowledge, Knowledge)
        self.assertEqual(knowledge.identity["email"], "cli@example.com")
        self.assertEqual(knowledge.identity["username"], "cliuser")


if __name__ == "__main__":
    unittest.main()
