import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from ai_analyst import AIAnalyst
from models import Knowledge


class TestPromptInjection(unittest.TestCase):
    @patch("asyncio.create_subprocess_exec")
    def test_knowledge_injection(self, mock_exec):
        # Configure mock to return a valid JSON object stringified
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (
            b'<answer>{"summary": "test"}</answer>',
            b"",
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        analyst = AIAnalyst(agent_type="ollama")
        knowledge = Knowledge(
            identity={"email": "certified@example.com"}, behavioral_tags=["verified"]
        )

        asyncio.run(analyst.analyze("some data", knowledge=knowledge))

        # Check if the command passed to create_subprocess_exec contains the knowledge
        found = False
        # mock_exec call args are (cmd[0], cmd[1], ..., stdout=..., stderr=...)
        for arg in mock_exec.call_args[0]:
            if "certified@example.com" in str(arg) and "CERTIFIED KNOWLEDGE" in str(
                arg
            ):
                found = True
                break

        self.assertTrue(found, "Knowledge grounding not found in LLM prompt")


if __name__ == "__main__":
    unittest.main()
