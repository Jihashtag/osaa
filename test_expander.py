import unittest
from identity_expander import IdentityExpander


class TestIdentityExpander(unittest.TestCase):
    def test_name_permutations(self):
        perms = IdentityExpander.generate_name_permutations("John Lambert")
        # Check for expected formats
        values = [p["value"] for p in perms]
        self.assertIn("johnlambert", values)
        self.assertIn("john.lambert", values)
        self.assertIn("john_lambert", values)
        self.assertIn("lambert_john", values)


if __name__ == "__main__":
    unittest.main()
