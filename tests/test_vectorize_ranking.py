"""Offline checks for lexical reranking; no Cloudflare credentials required."""
import unittest
from timdr_kb.vectorize_search import lexical_score, rank_matches

class RankingTests(unittest.TestCase):
    def test_chronoprocess_alias_in_filename(self):
        match = {"url": "https://github.com/org/repo/blob/sha/timdr_time/chronoprocess.py",
                 "excerpt": "Three independent projections"}
        self.assertGreater(lexical_score("chronoproces", match), 0)

    def test_relevant_filename_ranks_higher(self):
        items = [
            {"score": 0.61, "metadata": {"url": "https://github.com/x/README.md", "excerpt": "general introduction"}},
            {"score": 0.60, "metadata": {"url": "https://github.com/x/chronoprocess.py", "excerpt": "chronoproces"}},
        ]
        ranked = rank_matches("chronoproces", items)
        self.assertEqual(ranked[0][3]["metadata"]["url"], "https://github.com/x/chronoprocess.py")

    def test_semantic_only_keeps_similarity_order(self):
        items = [
            {"score": 0.61, "metadata": {"url": "https://github.com/x/README.md", "excerpt": ""}},
            {"score": 0.60, "metadata": {"url": "https://github.com/x/chronoprocess.py", "excerpt": "chronoproces"}},
        ]
        ranked = rank_matches("chronoproces", items, hybrid=False)
        self.assertEqual(ranked[0][1], 0.61)

if __name__ == "__main__":
    unittest.main()
