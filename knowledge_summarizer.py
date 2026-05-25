from typing import Optional
from osaa.ai_analyst import AIAnalyst


class KnowledgeSummarizer:
    """Utility to summarize large knowledge inputs using an LLM."""

    def __init__(self, analyst: Optional[AIAnalyst] = None):
        self.analyst = analyst or AIAnalyst()

    async def summarize(self, knowledge_text: str) -> str:
        """
        Summarizes the provided text into a concise knowledge base.
        Ensures PII and 'certified' facts are preserved while reducing noise.
        """
        prompt = f"""
        Summarize the following 'Knowledge' about a target. 
        Preserve all key facts (Names, Emails, Usernames, Locations, Jobs).
        Remove redundant text or fluff.
        Return the result as a JSON object with a 'summary' key.

        Knowledge:
        {knowledge_text}
        """

        result = await self.analyst.analyze(prompt)
        return result.get("summary", str(result))
