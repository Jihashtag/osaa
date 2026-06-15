"""E4.4 — username-only investigations derive candidate emails and run
account-existence connectors on them (results flagged speculative)."""

import tempfile
import unittest
from unittest.mock import AsyncMock

import path_utils
from connectors.base import DiscoveryResult
from models import IdentityAnchor
from orchestrator import Orchestrator
from identity_expander import IdentityExpander


class TestDeriveCandidateEmails(unittest.TestCase):
    def test_pure_helper(self):
        out = IdentityExpander.derive_candidate_emails("lolla_lamb15", limit=3)
        self.assertEqual(out[0], "lolla_lamb15@gmail.com")
        self.assertEqual(len(out), 3)
        self.assertEqual(IdentityExpander.derive_candidate_emails(""), [])


class TestSpeculativeChecks(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # identity_utils writes artifact files; anchor the report dir to a tmp.
        path_utils.BASE_PATH = tempfile.mkdtemp()
        path_utils.BASE_TARGET = "spec_test"

    async def test_holehe_run_on_derived_emails_and_flagged(self):
        orch = Orchestrator()
        orch.identity.username.append(IdentityAnchor(value="lolla_lamb15"))

        async def fake_holehe(target, proxies=None, **kwargs):
            return [DiscoveryResult("holehe", "account", "twitter", {"email": target})]

        orch.connectors["holehe"].run = AsyncMock(side_effect=fake_holehe)
        orch.connectors["breach"].run = AsyncMock(return_value=[])

        await orch._run_speculative_account_checks()

        called_emails = [c.args[0] for c in orch.connectors["holehe"].run.call_args_list]
        self.assertIn("lolla_lamb15@gmail.com", called_emails)
        # results recorded, flagged speculative, confidence-capped
        accounts = [a for a in orch.identity.raw_artifacts if a.target_type == "account"]
        self.assertTrue(accounts)
        self.assertTrue(all(a.metadata.get("speculative") for a in accounts))
        self.assertTrue(all(a.confidence <= 0.5 for a in accounts))

    async def test_skipped_when_email_known(self):
        orch = Orchestrator()
        orch.identity.username.append(IdentityAnchor(value="u"))
        orch.identity.email.append(IdentityAnchor(value="real@example.com"))
        orch.connectors["holehe"].run = AsyncMock(return_value=[])
        await orch._run_speculative_account_checks()
        orch.connectors["holehe"].run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
