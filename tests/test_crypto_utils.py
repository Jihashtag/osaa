import unittest
from identity_utils import sha256_hex


class TestCryptoUtils(unittest.TestCase):
    def test_hashing(self):
        # Correct hash for "test@example.com"
        expected = "973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b"
        self.assertEqual(sha256_hex("test@example.com"), expected)
        self.assertEqual(sha256_hex(" TEST@EXAMPLE.COM "), expected)


if __name__ == "__main__":
    unittest.main()
