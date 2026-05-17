import json
import os
from logger import get_logger
from typing import Dict, Any, List

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class AIReportWriter:
    def __init__(self, analyst):
        self.analyst = analyst
        self.potential_identities = {}

    def _sanitize_artifacts(self, artifacts: List[Any]) -> List[Dict[str, Any]]:
        sanitized = []
        for item in artifacts:
            metadata = item.metadata if hasattr(item, "metadata") else {}
            # Handle potential dict vs object for item
            item_val = (
                item.get("value", "")
                if isinstance(item, dict)
                else getattr(item, "value", "")
            )

            res = self.analyst.analyze(
                f"""\n\nAnalyze and extract from the following data every elements / data / informations related to {self.potential_identities} and determine if they are most likely the same or a different person:
If the data is not sufficent and ONLY if it is not sufficent, return a JSON key "error" explaining the reason.
Answer example:
<example>
{{
    "target": "<target identifiers>",
    "description": "<description of the artifact>",
    "additional_data": "<additional insight>"
}}
</example>

<example>
{{
    "error": "The artifact is a website error page"
}}
</example>

Source:
<data>
{{
    "title": "{str(metadata.get('title', 'N/A'))}",
    "value": "{str(item_val)}",
}}
</data>
"""
            )
            if isinstance(res, dict) and "error" not in res:
                sanitized.append(res)
            else:
                logger.info(f"[x] Artifact extraction invalid: {res}")
        return sanitized

    def _generate_section(self, section_name: str, prompt: str) -> str:
        normalized_key = section_name.lower().replace(" ", "_")
        try:
            full_prompt = f"{prompt}\n\nINSTRUCTIONS: Clearly separate verified facts from analytical assumptions. Ensure we mention the sources when available.\n**Return a JSON with ONLY the key '{normalized_key}'**."
            response = self.analyst.analyze(full_prompt)
            if isinstance(response, dict) and normalized_key in response:
                return response[normalized_key]
            if isinstance(response, dict) and response:
                # If the key is not found but there's other content, return it all joined
                return "\n".join(str(v) for v in response.values())
            return f"Section {section_name} generation failed."
        except Exception as e:
            return f"Section {section_name} error: {e}"

    def _generate_evidence_table(self, artifacts: List[Any]) -> str:
        if not artifacts:
            return "No evidence found."

        table = "| Source | Type | Value | Artifact |\n|---|---|---|---|\n"
        for item in artifacts:
            source = (
                item.get("source_tool", "N/A")
                if isinstance(item, dict)
                else getattr(item, "source_tool", "N/A")
            )
            ttype = (
                item.get("target_type", "N/A")
                if isinstance(item, dict)
                else getattr(item, "target_type", "N/A")
            )
            val = (
                str(item.get("value", "N/A"))
                if isinstance(item, dict)
                else str(getattr(item, "value", "N/A"))
            )
            meta = (
                item.get("metadata", {})
                if isinstance(item, dict)
                else getattr(item, "metadata", {})
            )
            raw = meta.get("raw_path", "N/A")
            if raw != "N/A":
                raw = os.path.basename(raw)
            table += f"| {source} | {ttype} | {val[:30]} | {raw} |\n"
        return table

    def generate_report(self, target: str, identity: Any) -> str:
        self.potential_identities = {
            "usernames": list(set(un for un in identity.username if un)),
            "fullname": list(set(fn for fn in identity.fullname if fn)),
            "email": list(set(mail for mail in identity.email if mail)),
        }
        sanitized_artifacts = self._sanitize_artifacts(identity.raw_artifacts)
        evidence_table = self._generate_evidence_table(identity.raw_artifacts)

        summary = self._generate_section(
            "Summary",
            f"{target} informations to summarize: {sanitized_artifacts}.",
        )
        profiling_data = self._generate_section(
            "Profiling", f"Create profile for {target} based on: {sanitized_artifacts}."
        )

        identities_md = f"### Identified Usernames: {', '.join(self.potential_identities['usernames'])}\n### Identified Full Names: {', '.join(self.potential_identities['fullname'])}\n### Identified Emails: {', '.join(self.potential_identities['email'])}"

        return f"# Intelligence Report: {target}\n\n## 0. Identities Identified\n{identities_md}\n\n## 1. Summary\n{summary}\n\n## 2. Profiling\n{profiling_data}\n\n## 3. Evidence Log\n{evidence_table}"
