import unittest
from fusion_engine import FusionEngine
from models import IdentityAnchor


class TestFusionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FusionEngine()

    def test_exact_match(self):
        anchor = IdentityAnchor(value="john.doe@gmail.com", aggregate_confidence=1.0)
        prob = self.engine.calculate_link_probability(
            "john.doe@gmail.com", anchor, "holehe"
        )
        # Fuzz=1.0, Trust=0.95 -> 1.0*0.6 + 0.95*0.3 = 0.6 + 0.285 = 0.885
        self.assertGreaterEqual(prob, 0.88)
        self.assertTrue(self.engine.is_link_valid(prob))

    def test_fuzzy_match(self):
        anchor = IdentityAnchor(value="johndoe", aggregate_confidence=1.0)
        prob = self.engine.calculate_link_probability("john.doe", anchor, "tookie")
        # Fuzz should be high (~0.9-1.0), Trust=0.85
        self.assertGreater(prob, 0.7)

    def test_domain_bonus(self):
        anchor = IdentityAnchor(value="target@proton.me", aggregate_confidence=1.0)
        prob_with_bonus = self.engine.calculate_link_probability(
            "other@proton.me", anchor, "holehe"
        )

        anchor_no_bonus = IdentityAnchor(
            value="target@gmail.com", aggregate_confidence=1.0
        )
        prob_no_bonus = self.engine.calculate_link_probability(
            "other@gmail.com", anchor_no_bonus, "holehe"
        )

        self.assertGreater(prob_with_bonus, prob_no_bonus)


if __name__ == "__main__":
    unittest.main()
