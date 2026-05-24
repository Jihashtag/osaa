import unittest
from reporters.review_engine import ReviewEngine
from models import MasterIdentity, IdentityAnchor


class TestReviewEngine(unittest.TestCase):
    def test_audit_pass(self):
        identity = MasterIdentity()
        identity.email.append(IdentityAnchor(value="test@example.com"))

        engine = ReviewEngine()
        report = engine.audit(identity)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["artifact_count"], 1)


if __name__ == "__main__":
    unittest.main()
