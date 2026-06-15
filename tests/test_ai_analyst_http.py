"""E3.6 — persistent HTTP LLM backends (no subprocess spawn, offline-mocked)."""

import json
import unittest
from unittest.mock import patch

from ai_analyst import AIAnalyst


class TestOllamaHttp(unittest.IsolatedAsyncioTestCase):
    async def test_parses_ollama_response(self):
        analyst = AIAnalyst(agent_type="ollama-http", model_name="llama3.2:1b")
        body = json.dumps({"response": '<answer>{"summary": "ok"}</answer>'})
        with patch.object(analyst, "_http_post", return_value=(200, body)) as m:
            with patch("asyncio.create_subprocess_exec") as proc:
                res = await analyst.analyze("data")
                proc.assert_not_called()  # no CLI spawned
        self.assertEqual(res["summary"], "ok")
        self.assertIn("/api/generate", m.call_args[0][0])

    async def test_non_200_returns_error(self):
        analyst = AIAnalyst(agent_type="ollama-http")
        with patch.object(analyst, "_http_post", return_value=(500, "boom")):
            res = await analyst.analyze("data")
        self.assertIn("error", res)

    async def test_exception_returns_error(self):
        analyst = AIAnalyst(agent_type="ollama-http")
        with patch.object(analyst, "_http_post", side_effect=OSError("conn refused")):
            res = await analyst.analyze("data")
        self.assertIn("error", res)


class TestLmsServer(unittest.IsolatedAsyncioTestCase):
    async def test_parses_openai_style_response(self):
        analyst = AIAnalyst(agent_type="lms-server", model_name="google/gemma-3n-e4b")
        body = json.dumps(
            {"choices": [{"message": {"content": '{"summary": "via-server"}'}}]}
        )
        with patch.object(analyst, "_http_post", return_value=(200, body)) as m:
            res = await analyst.analyze("data")
        self.assertEqual(res["summary"], "via-server")
        self.assertIn("/v1/chat/completions", m.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
