"""Locks the holehe fix: hits are 'account' artifacts, never email anchors."""

import subprocess
import unittest
from unittest.mock import patch, MagicMock

from connectors.holehe import HoleheConnector


class TestHoleheAccountType(unittest.IsolatedAsyncioTestCase):
    @patch("subprocess.run")
    async def test_hits_are_account_type(self, mock_run):
        mock_run.return_value = MagicMock(stdout="[+] twitter\n[-] github\n[+] reddit")
        results = await HoleheConnector().run("target@example.com")

        self.assertEqual([r.value for r in results], ["twitter", "reddit"])
        for r in results:
            # Must NOT be tagged 'email' (that would pollute identity anchors).
            self.assertEqual(r.target_type, "account")
            self.assertEqual(r.metadata["email"], "target@example.com")

    @patch("subprocess.run", side_effect=FileNotFoundError())
    async def test_missing_binary_returns_empty(self, _mock_run):
        self.assertEqual(await HoleheConnector().run("a@b.com"), [])

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired("holehe", 120))
    async def test_timeout_returns_empty(self, _mock_run):
        self.assertEqual(await HoleheConnector().run("a@b.com"), [])


if __name__ == "__main__":
    unittest.main()
