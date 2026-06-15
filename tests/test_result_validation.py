"""Unit tests for utils/result_validation.is_meaningful_result."""

import unittest

from utils.result_validation import is_meaningful_result


class TestMeaningfulResult(unittest.TestCase):
    def test_query_echo_is_rejected(self):
        self.assertFalse(is_meaningful_result("lolla_lamb15", "lolla_lamb15", []))
        self.assertFalse(is_meaningful_result("lolla_lamb15", "  Lolla_Lamb15 \n", None))

    def test_links_make_it_meaningful(self):
        self.assertTrue(
            is_meaningful_result(
                "lolla_lamb15", "lolla_lamb15", ["http://abc.onion/u"]
            )
        )

    def test_substantive_text_is_meaningful(self):
        self.assertTrue(
            is_meaningful_result(
                "lolla_lamb15",
                "Profile lolla_lamb15 — 42 posts, joined 2021, bio: medical student in Lille",
            )
        )

    def test_query_absent_is_rejected(self):
        self.assertFalse(is_meaningful_result("lolla_lamb15", "completely unrelated page content here"))

    def test_empty_inputs(self):
        self.assertFalse(is_meaningful_result("", "x"))
        self.assertFalse(is_meaningful_result("x", ""))


if __name__ == "__main__":
    unittest.main()
