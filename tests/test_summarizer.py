import unittest
import asyncio
from unittest.mock import MagicMock
from knowledge_summarizer import KnowledgeSummarizer


class TestKnowledgeSummarizer(unittest.TestCase):
    def test_summarize(self):
        mock_analyst = MagicMock()

        async def mock_analyze(*args, **kwargs):
            return {"summary": "A concise summary of the target."}

        mock_analyst.analyze = mock_analyze

        summarizer = KnowledgeSummarizer(mock_analyst)
        large_text = (
            "This is a very long text about a person that needs to be summarized. " * 50
        )
        summary = asyncio.run(summarizer.summarize(large_text))

        self.assertEqual(summary, "A concise summary of the target.")


if __name__ == "__main__":
    unittest.main()
