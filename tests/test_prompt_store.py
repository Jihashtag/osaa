import unittest
from ai_analyst import AIAnalyst


class TestPromptStore(unittest.TestCase):
    def test_prompt_loading(self):
        analyst = AIAnalyst()
        # Verify that the system prompt contains a known keyword from reviewer.md
        self.assertIn("Clinical Psychologist", analyst.system_prompt)
        self.assertIn("STRICTLY PROHIBITED", analyst.system_prompt)


if __name__ == "__main__":
    unittest.main()
