"""Tests for AIReportWriter: content extraction (E2), batching (E3.7),
evidence-log filtering (E4.1) and the corroboration section (E4.3)."""

import os
import tempfile
import unittest

from connectors.base import DiscoveryResult
from models import MasterIdentity, IdentityAnchor, Knowledge
from reporters.ai_report_writer import AIReportWriter


class RecordingAnalyst:
    """Captures prompts and returns canned structured output."""

    def __init__(self, response=None):
        self.prompts = []
        self.response = response or {"target": "t", "description": "d"}

    async def analyze(self, prompt, knowledge=None):
        self.prompts.append(prompt)
        if isinstance(self.response, list):
            return self.response[len(self.prompts) - 1]
        return self.response


class TestArtifactText(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.w = AIReportWriter(RecordingAnalyst())

    def test_reads_raw_path_truncated(self):
        with tempfile.NamedTemporaryFile("w", suffix=".raw", delete=False) as f:
            f.write("hello world " * 100)
            path = f.name
        art = DiscoveryResult("browser", "url", "https://x", {"raw_path": path})
        text = self.w._artifact_text(art, max_chars=50)
        self.assertEqual(len(text), 50)
        self.assertIn("hello world", text)
        os.unlink(path)

    def test_missing_raw_path_is_safe(self):
        art = DiscoveryResult("browser", "url", "https://x", {"raw_path": "/no/such"})
        self.assertEqual(self.w._artifact_text(art), "")

    def test_inline_content_preferred(self):
        art = DiscoveryResult("browser", "url", "https://x", {"content": "inline text"})
        self.assertEqual(self.w._artifact_text(art), "inline text")


class TestSanitizeIncludesContent(unittest.IsolatedAsyncioTestCase):
    async def test_prompt_contains_page_text_not_just_url(self):
        with tempfile.NamedTemporaryFile("w", suffix=".raw", delete=False) as f:
            f.write("telegram profile of lolla_lamb15 with bio")
            path = f.name
        analyst = RecordingAnalyst()
        w = AIReportWriter(analyst)
        w.potential_identities = {"usernames": ["lolla_lamb15"], "fullname": [], "email": []}
        await w._sanitize_artifacts(
            [DiscoveryResult("browser", "url", "https://t.me/lolla_lamb15", {"raw_path": path})]
        )
        joined = "\n".join(analyst.prompts)
        self.assertIn("telegram profile of lolla_lamb15", joined)
        os.unlink(path)


class TestSanitizeBatches(unittest.IsolatedAsyncioTestCase):
    async def test_single_call_for_a_batch_and_errors_dropped(self):
        # analyst returns ONE JSON array for the whole batch; one item is an error
        class ArrayAnalyst:
            def __init__(self):
                self.prompts = []

            async def analyze(self, prompt, knowledge=None):
                self.prompts.append(prompt)
                return [
                    {"target": "a", "description": "d1"},
                    {"error": "blank page"},
                    {"target": "c", "description": "d3"},
                    {"target": "d", "description": "d4"},
                    {"target": "e", "description": "d5"},
                ]

        analyst = ArrayAnalyst()
        w = AIReportWriter(analyst)
        w.potential_identities = {"usernames": ["u"], "fullname": [], "email": []}
        arts = [
            DiscoveryResult("browser", "url", f"https://x/{i}", {"content": f"c{i}"})
            for i in range(5)
        ]
        out = await w._sanitize_artifacts(arts, batch_size=8)
        self.assertEqual(len(analyst.prompts), 1)  # one batched call, not five
        self.assertEqual(len(out), 4)  # the error item dropped


class TestEvidenceTable(unittest.TestCase):
    def setUp(self):
        self.w = AIReportWriter(RecordingAnalyst())

    def test_serps_dropped_and_duplicates_clustered(self):
        arts = [
            DiscoveryResult("searcher", "url", f"https://yandex.com/search/?text={i}", {}, confidence=0.7)
            for i in range(10)
        ] + [
            DiscoveryResult("browser", "url", "https://t.me/lolla_lamb15", {"raw_path": "/x/a.raw"}, confidence=0.9),
            DiscoveryResult("browser", "url", "https://lolchess.gg/profile/x", {}, confidence=0.6),
        ]
        table = self.w._generate_evidence_table(arts)
        self.assertNotIn("yandex.com", table)  # SERPs filtered
        self.assertIn("t.me/lolla_lamb15", table)
        self.assertIn("lolchess.gg", table)
        self.assertIn("Confidence", table)
        self.assertIn("Reliability", table)

    def test_same_domain_clustered_with_count(self):
        arts = [
            DiscoveryResult("browser", "url", "https://t.me/a", {}, confidence=0.5),
            DiscoveryResult("browser", "url", "https://t.me/b", {}, confidence=0.9),
        ]
        table = self.w._generate_evidence_table(arts)
        # one clustered row for t.me, count 2, keeping the higher confidence
        rows = [r for r in table.splitlines() if "t.me" in r]
        self.assertEqual(len(rows), 1)
        self.assertIn("| 2 |", rows[0])
        self.assertIn("0.90", rows[0])


class TestCorroborationSection(unittest.IsolatedAsyncioTestCase):
    async def test_report_contains_corroboration_section(self):
        ident = MasterIdentity()
        ident.username.append(IdentityAnchor(value="lolla_lamb15"))
        ident.raw_artifacts.append(
            DiscoveryResult("browser", "url", "https://t.me/lolla_lamb15", {"content": "send message"})
        )
        knowledge = Knowledge(identity={"username": "lolla_lamb15", "location": "Lille"})
        w = AIReportWriter(RecordingAnalyst(response={"summary": "s"}))
        md = await w.generate_report("lolla_lamb15", ident, knowledge=knowledge)
        self.assertIn("## 2.1 Knowledge Corroboration", md)
        self.assertIn("location", md)
        self.assertIn("unconfirmed", md)  # Lille not in evidence


if __name__ == "__main__":
    unittest.main()
