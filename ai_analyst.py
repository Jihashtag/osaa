import json
import asyncio
from logger import get_logger
import os
import subprocess
import re
from typing import Dict, Any, Optional
from models import Knowledge

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class AIAnalyst:
    """Uses various AI agents (LM Studio, Ollama, Gemini) to analyze artifacts."""

    def __init__(self, agent_type: str = "lms", model_name: str = None):
        self.agent_type = agent_type.lower()
        self.model = model_name or self._get_default_model(self.agent_type)
        self.system_prompt = self._load_prompt("reviewer.md")

    def _load_prompt(self, filename: str) -> str:
        """Loads a prompt from the prompts directory."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "prompts", filename)
        if not os.path.exists(path):
            return "You are a helpful assistant."
        with open(path, "r") as f:
            return f.read().strip()

    def _get_default_model(self, agent_type: str) -> str:
        if agent_type == "lms":
            return "google/gemma-3-1b"
        elif agent_type == "ollama":
            return "llama3"
        elif agent_type == "gemini":
            return "gemini-2.0-flash"
        return "default"

    def _extract_json(self, text: str) -> Dict[str, Any]:
        # Clean ANSI escape codes
        text = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)

        try:
            start = text.find("<answer>")
            end = text.rfind("</answer>")
            if start != -1 and end != -1:
                json_str = text[start + 8 : end].strip()
                return json.loads(json_str)
        except Exception:
            pass
        try:
            # Check for markdown json block
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))

            # Fallback to first '{' and last '}'
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                json_str = text[start : end + 1].strip()
                return json.loads(json_str)
        except Exception:
            pass

        try:
            return json.loads(text)
        except Exception:
            return {"error": "Failed to parse JSON", "raw_output": text}

    async def analyze(
        self, identity_data: str, knowledge: Optional[Knowledge] = None
    ) -> Dict[str, Any]:
        """Analyzes OSINT artifacts via selected AI agent."""
        knowledge_context = ""
        if knowledge:
            knowledge_context = f"\n**CERTIFIED KNOWLEDGE (GROUND TRUTH):**\n{json.dumps(knowledge.to_dict(), indent=2)}\n"

        prompt = f"""
{self.system_prompt}
{knowledge_context}

Return a strictly **valid JSON object** under "<answer>" tags.
DO NOT USE placeholders like '<...>'. Write complete sentences.

**Run a deep and complete analysis based on:**
{identity_data}
        """

        if self.agent_type == "lms":
            cmd = [
                "lms",
                "chat",
                "--dont-fetch-catalog",
                "-y",
                self.model,
                "-s",
                self.system_prompt,
                "-p",
                prompt,
            ]
        elif self.agent_type == "ollama":
            # For Ollama, we combine system prompt and prompt if needed
            full_prompt = f"{self.system_prompt}\n\n{prompt}"
            cmd = [
                "ollama",
                "run",
                self.model,
                full_prompt,
                "--experimental-yolo",
                "--format",
                "json",
            ]
        elif self.agent_type == "gemini":
            # Using the gemini CLI with --prompt
            cmd = ["gemini", "--prompt", prompt]
        else:
            return {"error": f"Unsupported agent type: {self.agent_type}"}

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)

            if process.returncode != 0:
                return {"error": f"{self.agent_type} command failed: {stderr.decode()}"}

            stdout_str = stdout.decode()
            if os.getenv("DEBUG") == "True":
                logger.info(
                    f"{self.agent_type.upper()} Raw Output: {stdout_str[:500]}..."
                )

            return self._extract_json(stdout_str)
        except asyncio.TimeoutError:
            return {"error": f"Analysis timed out for {self.agent_type}"}
        except Exception as e:
            return {"error": f"Analysis service unavailable: {e}"}
