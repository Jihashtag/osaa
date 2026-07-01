import json
import os
from logger import get_logger
from typing import Dict, Any, List

from utils.config import load_reliability_weights
from utils.url_filter import is_search_engine_url, registered_domain
from reporters.corroboration import assess
from reporters.review_engine import ReviewEngine

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


class AIReportWriter:
    def __init__(self, analyst):
        self.analyst = analyst
        self.potential_identities = {}
        self.knowledge = None

    @staticmethod
    def _meta(item) -> Dict[str, Any]:
        if isinstance(item, dict):
            return item.get("metadata", {}) or {}
        return getattr(item, "metadata", {}) or {}

    @staticmethod
    def _val(item) -> str:
        if isinstance(item, dict):
            return str(item.get("value", ""))
        return str(getattr(item, "value", ""))

    def _artifact_text(self, item, *, max_chars: int = 2000) -> str:
        """Return the captured page text for an artifact (the real evidence).

        Prefers an inline ``metadata['content']``; otherwise reads the on-disk
        ``metadata['raw_path']`` file. Missing files are tolerated (returns "").
        Whitespace is collapsed and the text truncated to ``max_chars`` so the
        analysis prompt stays bounded."""
        meta = self._meta(item)
        text = meta.get("content")
        if not text:
            raw = meta.get("raw_path")
            if raw and os.path.exists(raw):
                try:
                    with open(raw, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    text = ""
        text = (text or "").replace("\x00", "")
        text = " ".join(text.split())
        return text[:max_chars]

    async def _sanitize_artifacts(
        self, artifacts: List[Any], knowledge: Any = None, *, batch_size: int = 8
    ) -> List[Dict[str, Any]]:
        """Extract structured insight from artifacts, sending the actual page
        CONTENT (not just the URL) to the analyst, batched to cut LLM calls."""
        sanitized: List[Dict[str, Any]] = []
        records = [
            {
                "title": str(self._meta(item).get("title", "N/A")),
                "value": self._val(item),
                "content": self._artifact_text(item),
            }
            for item in artifacts
        ]
        if not records:
            return sanitized

        for start in range(0, len(records), batch_size):
            chunk = records[start : start + batch_size]
            res = await self.analyst.analyze(
                f"""\n\nAnalyze the following {len(chunk)} OSINT artifact(s) and, for EACH, extract every element/data/information related to {self.potential_identities} and judge whether it is the same or a different person.

Return a JSON ARRAY with one object per artifact, in order. For an artifact with insufficient data, return an object with a single key "error".
Answer example:
<example>
[
  {{"target": "<identifiers>", "description": "<what the artifact shows>", "additional_data": "<insight>"}},
  {{"error": "The artifact is a website error page"}}
]
</example>

Artifacts:
<data>
{json.dumps(chunk, ensure_ascii=False)}
</data>
""",
                knowledge=knowledge,
            )
            if isinstance(res, dict) and "error" in res and len(res) == 1:
                # The whole batch failed at the backend level (unreachable
                # server, timeout, bad model) rather than a per-artifact
                # parsing issue — this is worth the user's attention now,
                # not just buried later as "no data" in the report.
                logger.warning(
                    f"[!] AI backend error while sanitizing artifacts: {res['error']}"
                )
                continue
            for parsed in self._coerce_array(res, len(chunk)):
                if isinstance(parsed, dict) and "error" not in parsed and parsed:
                    sanitized.append(parsed)
                else:
                    logger.info(f"[x] Artifact extraction invalid: {parsed}")
        return sanitized

    @staticmethod
    def _coerce_array(res: Any, expected: int) -> List[Any]:
        """Normalise the analyst response to a list of per-artifact dicts."""
        if isinstance(res, list):
            return res
        if isinstance(res, dict):
            # Some models wrap the array under a key, or return a single object.
            for v in res.values():
                if isinstance(v, list):
                    return v
            return [res]
        return [{"error": "unparseable analyst response"}]

    async def _generate_section(
        self, section_name: str, prompt: str, knowledge: Any = None
    ) -> str:
        normalized_key = section_name.lower().replace(" ", "_")
        try:
            full_prompt = f"{prompt}\n\nINSTRUCTIONS: Clearly separate verified facts from analytical assumptions. Ensure we mention the sources when available.\n**Return a JSON with ONLY the key '{normalized_key}'**."
            response = await self.analyst.analyze(full_prompt, knowledge=knowledge)
            if isinstance(response, dict) and "error" in response:
                # Surface backend failures immediately instead of letting them
                # sit silently inside the generated Markdown until read later.
                logger.warning(
                    f"[!] AI backend error while generating '{section_name}': {response['error']}"
                )
                return f"_Section unavailable — AI backend error: {response['error']}_"
            if isinstance(response, dict) and normalized_key in response:
                return response[normalized_key]
            if isinstance(response, dict) and response:
                # If the key is not found but there's other content, return it all joined
                return "\n".join(str(v) for v in response.values())
            return f"Section {section_name} generation failed."
        except Exception as e:
            logger.warning(f"[!] Exception generating '{section_name}': {e}")
            return f"Section {section_name} error: {e}"

    @staticmethod
    def _attr(item, name, default=None):
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    def _generate_evidence_table(self, artifacts: List[Any]) -> str:
        """Evidence log: drop SERP rows, cluster duplicates by domain, and show
        a confidence + source-reliability column so weak links are visible."""
        if not artifacts:
            return "No evidence found."

        weights = load_reliability_weights() or {}
        # Cluster by (source_tool, registered domain of value); keep the highest
        # confidence sighting and count duplicates.
        clusters: Dict[Any, Dict[str, Any]] = {}
        order: List[Any] = []
        for item in artifacts:
            val = str(self._attr(item, "value", "N/A"))
            if is_search_engine_url(val):
                continue  # SERP, not evidence
            source = self._attr(item, "source_tool", "N/A")
            ttype = self._attr(item, "target_type", "N/A")
            conf = float(self._attr(item, "confidence", 1.0) or 1.0)
            meta = self._attr(item, "metadata", {}) or {}
            raw = meta.get("raw_path", "")
            key = (source, registered_domain(val) or val)
            if key not in clusters:
                clusters[key] = {
                    "source": source,
                    "type": ttype,
                    "value": val,
                    "conf": conf,
                    "raw": os.path.basename(raw) if raw else "N/A",
                    "count": 1,
                }
                order.append(key)
            else:
                c = clusters[key]
                c["count"] += 1
                if conf > c["conf"]:
                    c["conf"], c["value"] = conf, val

        if not order:
            return "No evidence found (search-engine result pages were filtered out)."

        table = (
            "| Source | Reliability | Confidence | Type | Value | Seen | Artifact |\n"
            "|---|---|---|---|---|---|---|\n"
        )
        for key in order:
            c = clusters[key]
            rel = weights.get(c["source"], 0.5)
            table += (
                f"| {c['source']} | {rel:.2f} | {c['conf']:.2f} | {c['type']} | "
                f"{c['value'][:40]} | {c['count']} | {c['raw']} |\n"
            )
        return table

    def _generate_corroboration_table(self, identity: Any, knowledge: Any) -> str:
        """Mark which certified-knowledge facts the OSINT evidence supports."""
        if not knowledge:
            return "No certified knowledge supplied."
        texts = [self._artifact_text(a) for a in getattr(identity, "raw_artifacts", [])]
        rows = assess(knowledge, texts)
        if not rows:
            return "No biographical knowledge facts to corroborate."
        table = "| Fact | Value | Status | Evidence |\n|---|---|---|---|\n"
        for r in rows:
            table += (
                f"| {r['fact']} | {r['value']} | {r['status']} | {r['evidence'] or '—'} |\n"
            )
        return table

    @staticmethod
    def _generate_audit_section(identity: Any) -> str:
        """Runs ReviewEngine over the fused identity and renders its
        findings — distinct anchors that didn't get merged, low-confidence
        anchors — so an analyst sees them instead of the report silently
        treating every anchor as equally certain."""
        report = ReviewEngine().audit(identity)
        if not report["warnings"]:
            return (
                f"Status: {report['status']} — no conflicts detected across "
                f"{report['artifact_count']} identity anchor(s)."
            )
        lines = [f"Status: {report['status']}", ""]
        lines.extend(f"- {w}" for w in report["warnings"])
        return "\n".join(lines)

    async def generate_report(
        self, target: str, identity: Any, knowledge: Any = None
    ) -> str:
        self.knowledge = knowledge
        self.potential_identities = {
            "usernames": list(set(un.value for un in identity.username if un)),
            "fullname": list(set(fn for fn in identity.fullname if fn)),
            "email": list(set(mail.value for mail in identity.email if mail)),
        }
        sanitized_artifacts = await self._sanitize_artifacts(
            identity.raw_artifacts, knowledge=knowledge
        )
        evidence_table = self._generate_evidence_table(identity.raw_artifacts)
        corroboration_table = self._generate_corroboration_table(identity, knowledge)
        audit_section = self._generate_audit_section(identity)

        summary = await self._generate_section(
            "Summary",
            f"{target} informations to summarize: {sanitized_artifacts}.",
            knowledge=knowledge,
        )
        profiling_data = await self._generate_section(
            "Profiling",
            f"Create profile for {target} based on: {sanitized_artifacts}.",
            knowledge=knowledge,
        )

        identities_md = f"### Identified Usernames: {', '.join(self.potential_identities['usernames'])}\n### Identified Full Names: {', '.join(self.potential_identities['fullname'])}\n### Identified Emails: {', '.join(self.potential_identities['email'])}"

        return (
            f"# Intelligence Report: {target}\n\n"
            f"## 0. Identities Identified\n{identities_md}\n\n"
            f"## 1. Summary\n{summary}\n\n"
            f"## 2. Profiling\n{profiling_data}\n\n"
            f"## 2.1 Knowledge Corroboration\n{corroboration_table}\n\n"
            f"## 2.2 Data Quality Audit\n{audit_section}\n\n"
            f"## 3. Evidence Log\n{evidence_table}"
        )
