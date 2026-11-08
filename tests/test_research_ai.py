"""Unit tests for TIMDR Research AI; no network or API keys required."""
import unittest
from timdr_kb.research_ai import build_context, INSTRUCTIONS

class ResearchAITests(unittest.TestCase):
    def test_context_source_labels(self):
        sources = [{"id":"S1","url":"https://github.com/jbackk-lang/GIA-TIMDR/blob/main/README.md",
                    "branch":"cross_branch","status":"source_unverified","excerpt":"Chronoproces"}]
        context = build_context(sources)
        self.assertIn("[S1]", context)
        self.assertIn("Chronoproces", context)
        self.assertIn("source_unverified", context)

    def test_instructions_require_source_grounding(self):
        self.assertIn("[S1]", INSTRUCTIONS)
        self.assertIn("niezależnej walidacji", INSTRUCTIONS)

if __name__ == "__main__":
    unittest.main()
