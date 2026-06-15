"""E4.2 — knowledge-vs-findings corroboration (pure)."""

import unittest

from models import Knowledge
from reporters.corroboration import assess


class TestCorroboration(unittest.TestCase):
    def setUp(self):
        self.knowledge = Knowledge(
            identity={
                "username": "lolla_lamb15",  # seed -> not a biographical fact
                "location": "Lille",
                "occupation": "medical student",
            }
        )

    def test_unconfirmed_when_only_handle_found(self):
        rows = assess(self.knowledge, ["telegram profile of lolla_lamb15, send message"])
        by = {r["fact"]: r["status"] for r in rows}
        self.assertNotIn("username", by)  # seed excluded
        self.assertEqual(by["location"], "unconfirmed")
        self.assertEqual(by["occupation"], "unconfirmed")

    def test_corroborated_when_text_supports_facts(self):
        rows = assess(
            self.knowledge,
            ["bio: medical student living in Lille, France; 42 posts"],
        )
        by = {r["fact"]: r["status"] for r in rows}
        self.assertEqual(by["location"], "corroborated")
        self.assertEqual(by["occupation"], "corroborated")

    def test_partial_when_some_tokens_match(self):
        rows = assess(self.knowledge, ["a student page, no city given"])
        by = {r["fact"]: r["status"] for r in rows}
        self.assertEqual(by["occupation"], "partial")  # 'student' yes, 'medical' no
        self.assertEqual(by["location"], "unconfirmed")

    def test_handles_dict_knowledge_and_empty(self):
        self.assertEqual(assess(Knowledge(identity={}), ["x"]), [])
        rows = assess({"identity": {"location": "Lille"}}, ["lille is nice"])
        self.assertEqual(rows[0]["status"], "corroborated")


if __name__ == "__main__":
    unittest.main()
