"""An unconfigured holmes checkout ("could not even attempt this") must raise,
not silently return [] — Orchestrator's discovery cache relies on that to
tell a real error apart from a genuine "ran fine, found nothing"."""

import os
import tempfile
import unittest

from connectors.holmes import HolmesConnector


def _bare_holmes_dir():
    """A holmes_dir that exists but has no Configuration/Configuration.ini."""
    return tempfile.mkdtemp()


class TestHolmesRaisesWhenUnconfigured(unittest.IsolatedAsyncioTestCase):
    async def test_email_target_raises(self):
        connector = HolmesConnector(holmes_dir=_bare_holmes_dir())
        with self.assertRaises(Exception):
            await connector.run("someone@example.com")

    async def test_username_target_raises(self):
        connector = HolmesConnector(holmes_dir=_bare_holmes_dir())
        with self.assertRaises(Exception):
            await connector.run("someusername")

    async def test_invalid_dir_raises(self):
        connector = HolmesConnector(holmes_dir="/no/such/holmes/checkout")
        with self.assertRaises(Exception):
            await connector.run("someone@example.com")

    async def test_cwd_restored_after_failure(self):
        original = os.getcwd()
        connector = HolmesConnector(holmes_dir=_bare_holmes_dir())
        with self.assertRaises(Exception):
            await connector.run("someone@example.com")
        self.assertEqual(os.getcwd(), original)


if __name__ == "__main__":
    unittest.main()
