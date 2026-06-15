"""Unit tests for the local-noise blocklist filter."""

import unittest

from blocklist import is_local_noise


class TestBlocklist(unittest.TestCase):
    def test_exact_project_names_are_noise(self):
        for value in ["osaa", "venv", ".git", "python_holmes", "OSAA"]:
            self.assertTrue(is_local_noise(value), value)

    def test_source_files_are_noise(self):
        self.assertTrue(is_local_noise("orchestrator.py"))
        self.assertTrue(is_local_noise("module.PYC"))

    def test_path_segments_are_noise(self):
        self.assertTrue(is_local_noise("/home/u/proj/__pycache__/x"))
        self.assertTrue(is_local_noise("https://host/repo/.git/config"))

    def test_legitimate_values_are_not_noise(self):
        # These previously risked false positives from naive substring matches.
        for value in [
            "john_doe",
            "alice@example.com",
            "https://blog.python.org/post",
            "https://example.com/profile/pythonista",
            "sherlock_holmes",  # contains 'holmes' but is not the exact token
        ]:
            self.assertFalse(is_local_noise(value), value)


if __name__ == "__main__":
    unittest.main()
