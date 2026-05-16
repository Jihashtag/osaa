import unittest
from unittest.mock import patch, MagicMock
from connectors.holehe import HoleheConnector
from profiles import Profiles


class TestHoleheConnector(unittest.IsolatedAsyncioTestCase):
    @patch("subprocess.run")
    async def test_run(self, mock_run):
        # Mocking the holele run command output
        mock_output = MagicMock()
        mock_output.stdout = "[+] twitter\n[+] instagram"
        mock_run.return_value = mock_output

        connector = HoleheConnector()
        results = await connector.run("test@example.com")

        self.assertEqual(len(results), 2)
        self.assertIn("twitter", results[0].value)
        self.assertEqual(results[0].metadata["used"], True)


if __name__ == "__main__":
    unittest.main()
