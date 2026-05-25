import unittest
import json
from models import Knowledge


class TestKnowledgeModel(unittest.TestCase):
    """
    Test suite for the Knowledge model in osaa/models.py.
    """

    def test_instantiation_and_to_dict(self):
        """
        Tests that Knowledge can be instantiated and converted to a dictionary.
        """
        identity = {"email": "test@example.com", "fullname": "Test User"}
        tags = ["active", "developer"]
        meta = {"source": "github"}

        k = Knowledge(identity=identity, behavioral_tags=tags, metadata=meta)

        self.assertEqual(k.identity, identity)
        self.assertEqual(k.behavioral_tags, tags)
        self.assertEqual(k.metadata, meta)

        d = k.to_dict()
        self.assertEqual(d["identity"], identity)
        self.assertEqual(d["behavioral_tags"], tags)
        self.assertEqual(d["metadata"], meta)

    def test_to_json_string(self):
        """
        Tests that Knowledge can be serialized to a JSON string.
        """
        identity = {"email": "test@example.com"}
        k = Knowledge(identity=identity)
        json_str = k.to_json_string()

        # Load it back to verify
        data = json.loads(json_str)
        self.assertEqual(data["identity"]["email"], "test@example.com")
        self.assertEqual(data["behavioral_tags"], [])
        self.assertEqual(data["metadata"], {})

    def test_validate_valid_email(self):
        """
        Tests that validate() passes for a valid email.
        """
        k = Knowledge(identity={"email": "valid@example.com"})
        try:
            k.validate()
        except ValueError:
            self.fail("validate() raised ValueError unexpectedly!")

    def test_validate_invalid_email(self):
        """
        Tests that validate() raises ValueError for an invalid email.
        """
        k = Knowledge(identity={"email": "invalid-email"})
        with self.assertRaises(ValueError):
            k.validate()

    def test_validate_no_email(self):
        """
        Tests that validate() passes when no email is present in identity.
        """
        k = Knowledge(identity={"fullname": "Just Name"})
        try:
            k.validate()
        except ValueError:
            self.fail("validate() raised ValueError unexpectedly!")


if __name__ == "__main__":
    unittest.main()
