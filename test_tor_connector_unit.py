import unittest
from unittest.mock import MagicMock, patch
from connectors.tor import TorConnector
from connectors.base import DiscoveryResult


class TestTorConnector(unittest.TestCase):
    def setUp(self):
        self.connector = TorConnector()

    @patch("subprocess.check_output")
    def test_is_tor_running_true(self, mock_output):
        mock_output.return_value = b"tor\n"
        self.assertTrue(self.connector._is_tor_running())

    @patch("subprocess.check_output")
    def test_is_tor_running_false(self, mock_output):
        from subprocess import CalledProcessError

        mock_output.side_effect = CalledProcessError(1, "pgrep")
        self.assertFalse(self.connector._is_tor_running())

    @patch("connectors.tor.stealth")
    @patch("connectors.tor.uc.Chrome")
    def test_setup_driver_proxy(self, mock_chrome, mock_stealth):
        # Verify that proxy-server argument is passed to ChromeOptions
        with patch("connectors.tor.uc.ChromeOptions") as mock_options:
            self.connector._setup_driver()
            # Check if any call to add_argument included the tor proxy
            proxy_arg_found = False
            for call in mock_options.return_value.add_argument.call_args_list:
                if "--proxy-server=socks5://127.0.0.1:9050" in call[0][0]:
                    proxy_arg_found = True
            self.assertTrue(proxy_arg_found)


if __name__ == "__main__":
    unittest.main()
