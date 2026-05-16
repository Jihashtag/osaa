import unittest
from unittest.mock import patch, MagicMock
from ai_analyst import AIAnalyst


class TestAIAnalyst(unittest.TestCase):
    def test_lms_command(self):
        analyst = AIAnalyst(agent_type="lms", model_name="test-model")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout='<answer>{"summary": "test"}</answer>', stderr=""
            )
            res = analyst.analyze("some data")
            self.assertEqual(res["summary"], "test")
            cmd = mock_run.call_args[0][0]
            self.assertIn("lms", cmd)
            self.assertIn("test-model", cmd)

    def test_ollama_command(self):
        analyst = AIAnalyst(agent_type="ollama", model_name="llama3")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout='{"summary": "test"}', stderr=""
            )
            res = analyst.analyze("some data")
            self.assertEqual(res["summary"], "test")
            cmd = mock_run.call_args[0][0]
            self.assertIn("ollama", cmd)
            self.assertIn("llama3", cmd)

    def test_gemini_command(self):
        analyst = AIAnalyst(agent_type="gemini")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout='```json\n{"summary": "test"}\n```', stderr=""
            )
            res = analyst.analyze("some data")
            self.assertEqual(res["summary"], "test")
            cmd = mock_run.call_args[0][0]
            self.assertIn("gemini", cmd)
            self.assertIn("--prompt", cmd)


if __name__ == "__main__":
    unittest.main()
