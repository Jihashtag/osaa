import unittest
from connectors.base import DiscoveryResult


class TestDiscoveryResult(unittest.TestCase):
    def test_instantiation(self):
        # Test with mandatory fields
        res = DiscoveryResult(
            source_tool="test_tool",
            target_type="email",
            value="test@example.com",
            metadata={"raw": "data"},
        )
        self.assertEqual(res.confidence, 1.0)
        self.assertEqual(res.meta, {})

    def test_custom_fields(self):
        # Test with optional fields
        res = DiscoveryResult(
            source_tool="test_tool",
            target_type="email",
            value="test@example.com",
            metadata={"raw": "data"},
            confidence=0.8,
            meta={"taint": "low"},
        )
        self.assertEqual(res.confidence, 0.8)
        self.assertEqual(res.meta["taint"], "low")


if __name__ == "__main__":
    unittest.main()
