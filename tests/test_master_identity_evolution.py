import unittest
from models import MasterIdentity, IdentityAnchor
from connectors.base import DiscoveryResult
from identity_utils import update_identity_from_results
import path_utils
import os
import shutil


class TestMasterIdentityEvolution(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_reports"
        os.makedirs(self.test_dir, exist_ok=True)
        path_utils.get_report_dir("test_target", base_path=self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_anchor_aggregation(self):
        identity = MasterIdentity()
        results = [
            DiscoveryResult(
                source_tool="holehe",
                target_type="email",
                value="test@example.com",
                metadata={},
                confidence=0.9,
            ),
            DiscoveryResult(
                source_tool="tookie",
                target_type="username",
                value="testuser",
                metadata={},
                confidence=0.8,
            ),
        ]
        update_identity_from_results(identity, results)

        self.assertEqual(len(identity.email), 1)
        self.assertIsInstance(identity.email[0], IdentityAnchor)
        self.assertEqual(identity.email[0].value, "test@example.com")
        self.assertEqual(identity.email[0].aggregate_confidence, 0.9)

        self.assertEqual(len(identity.username), 1)
        self.assertEqual(identity.username[0].value, "testuser")
        self.assertEqual(identity.username[0].aggregate_confidence, 0.8)

    def test_duplicate_handling(self):
        identity = MasterIdentity()
        results = [
            DiscoveryResult(
                source_tool="h1", target_type="email", value="a@b.com", metadata={}
            ),
            DiscoveryResult(
                source_tool="h2", target_type="email", value="a@b.com", metadata={}
            ),
        ]
        update_identity_from_results(identity, results)
        self.assertEqual(len(identity.email), 1)


if __name__ == "__main__":
    unittest.main()
