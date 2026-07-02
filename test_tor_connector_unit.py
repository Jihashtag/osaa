import asyncio
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import path_utils
from connectors.tor import TorConnector
from connectors.base import DiscoveryResult


class TestTorConnector(unittest.TestCase):
    def setUp(self):
        self.connector = TorConnector()
        # .run() anchors its resource dir via path_utils; give it a sandbox.
        path_utils.BASE_PATH = tempfile.mkdtemp()
        path_utils.BASE_TARGET = "test_target"

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

    @patch("connectors.tor.TorConnector._is_tor_running", return_value=False)
    def test_run_raises_when_daemon_down(self, _mock_running):
        # Must raise (not return []) so Orchestrator's cache treats this as
        # an error to retry, not a verified "found nothing" to cache for a day.
        with self.assertRaises(RuntimeError):
            asyncio.run(self.connector.run("target"))

    @patch("connectors.tor.TorConnector._setup_driver", return_value=None)
    @patch("connectors.tor.TorConnector._is_tor_running", return_value=True)
    def test_run_raises_when_driver_init_fails(self, _mock_running, _mock_driver):
        with self.assertRaises(RuntimeError):
            asyncio.run(self.connector.run("target"))


if __name__ == "__main__":
    unittest.main()
