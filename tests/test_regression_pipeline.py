"""
Regression tests for OSAA pipeline.
Ensures that changes to core components don't break existing functionality.
"""

import unittest
import os
import tempfile
import shutil
from models import MasterIdentity, IdentityAnchor
from connectors.base import DiscoveryResult
from identity_utils import update_identity_from_results
from reporters.graph import GraphReporter
from reporters.review_engine import ReviewEngine
from fusion_engine import FusionEngine
import path_utils


class TestCoreIntegration(unittest.TestCase):
    """Tests core integration between models and utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        path_utils.get_report_dir("test_target", base_path=self.test_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_identity_anchor_compatibility(self):
        """Verify IdentityAnchor works with MasterIdentity."""
        identity = MasterIdentity()
        anchor = IdentityAnchor(value="test@example.com", aggregate_confidence=0.9)
        identity.email.append(anchor)

        self.assertEqual(len(identity.email), 1)
        self.assertEqual(identity.email[0].value, "test@example.com")
        self.assertEqual(identity.email[0].aggregate_confidence, 0.9)

    def test_discovery_result_to_identity_flow(self):
        """Verify DiscoveryResult flows correctly to MasterIdentity."""
        identity = MasterIdentity()

        results = [
            DiscoveryResult(
                source_tool="holehe",
                target_type="email",
                value="user@example.com",
                metadata={"verified": True},
                confidence=0.95,
            ),
            DiscoveryResult(
                source_tool="tookie",
                target_type="username",
                value="username123",
                metadata={"platform": "github"},
                confidence=0.85,
            ),
        ]

        update_identity_from_results(identity, results)

        self.assertEqual(len(identity.email), 1)
        self.assertEqual(len(identity.username), 1)
        self.assertEqual(identity.email[0].value, "user@example.com")
        self.assertEqual(identity.email[0].aggregate_confidence, 0.95)
        self.assertEqual(identity.username[0].value, "username123")
        self.assertEqual(identity.username[0].aggregate_confidence, 0.85)

    def test_graph_building_from_identity(self):
        """Verify GraphReporter correctly builds from IdentityAnchor."""
        identity = MasterIdentity()
        identity.email.append(
            IdentityAnchor(value="a@example.com", aggregate_confidence=1.0)
        )
        identity.username.append(
            IdentityAnchor(value="user_a", aggregate_confidence=0.9)
        )
        identity.discovered_urls.append("https://example.com/user_a")

        reporter = GraphReporter()
        reporter.build_from_identity(identity)

        # Should have: Subject + 1 email + 1 username + 1 url = 4 nodes
        self.assertEqual(len(reporter.graph.nodes()), 4)
        self.assertIn("Subject", reporter.graph.nodes())
        self.assertIn("a@example.com", reporter.graph.nodes())
        self.assertIn("user_a", reporter.graph.nodes())

    def test_review_engine_audit(self):
        """Verify ReviewEngine can audit MasterIdentity with IdentityAnchors."""
        identity = MasterIdentity()
        identity.email.append(IdentityAnchor(value="test@example.com"))
        identity.username.append(IdentityAnchor(value="testuser"))

        engine = ReviewEngine()
        report = engine.audit(identity)

        self.assertEqual(report["artifact_count"], 2)
        self.assertEqual(report["status"], "PASS")


class TestFusionEngineWithAnchors(unittest.TestCase):
    """Tests FusionEngine works with IdentityAnchor objects."""

    def setUp(self):
        self.engine = FusionEngine()

    def test_link_probability_calculation(self):
        """Verify link probability works with IdentityAnchor."""
        anchor = IdentityAnchor(value="john@gmail.com", aggregate_confidence=1.0)
        prob = self.engine.calculate_link_probability(
            "john@gmail.com", anchor, "holehe"
        )

        # Exact match with high-trust source should give high probability
        self.assertGreater(prob, 0.8)

    def test_fuzzy_matching_with_anchor(self):
        """Verify fuzzy matching works with IdentityAnchor."""
        anchor = IdentityAnchor(value="johndoe", aggregate_confidence=1.0)
        prob1 = self.engine.calculate_link_probability("john.doe", anchor, "tookie")
        prob2 = self.engine.calculate_link_probability("janedoe", anchor, "tookie")

        # Similar string should have higher probability than dissimilar
        self.assertGreater(prob1, prob2)


class TestDataModelConsistency(unittest.TestCase):
    """Tests that data models remain consistent and backward compatible."""

    def test_master_identity_with_empty_anchors(self):
        """Verify MasterIdentity works with empty anchor lists."""
        identity = MasterIdentity()
        self.assertEqual(len(identity.email), 0)
        self.assertEqual(len(identity.username), 0)
        self.assertIsInstance(identity.email, list)
        self.assertIsInstance(identity.username, list)

    def test_discovery_result_defaults(self):
        """Verify DiscoveryResult defaults work correctly."""
        result = DiscoveryResult(
            source_tool="test",
            target_type="email",
            value="test@example.com",
            metadata={},
        )

        # Should have default confidence and meta
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.meta, {})

    def test_discovery_result_custom_values(self):
        """Verify DiscoveryResult can be customized."""
        result = DiscoveryResult(
            source_tool="test",
            target_type="email",
            value="test@example.com",
            metadata={"raw": "data"},
            confidence=0.7,
            meta={"taint": "medium"},
        )

        self.assertEqual(result.confidence, 0.7)
        self.assertEqual(result.meta["taint"], "medium")


if __name__ == "__main__":
    unittest.main()
