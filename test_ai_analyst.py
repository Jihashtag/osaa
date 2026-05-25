import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from ai_analyst import AIAnalyst


class TestAIAnalyst(unittest.TestCase):
    @patch("asyncio.create_subprocess_exec")
    def test_lms_command(self, mock_exec):
        analyst = AIAnalyst(agent_type="lms", model_name="test-model")

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (
            b'<answer>{"summary": "test"}</answer>',
            b"",
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        res = asyncio.run(analyst.analyze("some data"))
        self.assertEqual(res["summary"], "test")

        args = mock_exec.call_args[0]
        self.assertIn("lms", args)
        self.assertIn("test-model", args)

    @patch("asyncio.create_subprocess_exec")
    def test_ollama_command(self, mock_exec):
        analyst = AIAnalyst(agent_type="ollama", model_name="llama3")

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b'{"summary": "test"}', b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        res = asyncio.run(analyst.analyze("some data"))
        self.assertEqual(res["summary"], "test")

        args = mock_exec.call_args[0]
        self.assertIn("ollama", args)
        self.assertIn("llama3", args)

    @patch("asyncio.create_subprocess_exec")
    def test_gemini_command(self, mock_exec):
        analyst = AIAnalyst(agent_type="gemini")

        mock_process = AsyncMock()
        mock_process.communicate.return_value = (
            b'```json\n{"summary": "test"}\n```',
            b"",
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        res = asyncio.run(analyst.analyze("some data"))
        self.assertEqual(res["summary"], "test")

        args = mock_exec.call_args[0]
        self.assertIn("gemini", args)
        self.assertIn("--prompt", args)


if __name__ == "__main__":
    unittest.main()
