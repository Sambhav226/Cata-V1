"""Retrieval must generalise past exact catalogue phrasing — see
skills/clinical-retrieval."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coder.retrieval import Retriever


class RetrievalTest(unittest.TestCase):
    def setUp(self):
        self.retriever = Retriever()

    def test_synonym_not_exact_title_still_matches(self):
        # "bacillary dysentery" is a synonym for Shigellosis (1A03), not the title
        codes = self.retriever.candidate_codes("Patient has bacillary dysentery symptoms")
        self.assertTrue(any(c.entry.code == "1A03" for c in codes))

    def test_unrelated_text_returns_no_confident_candidates(self):
        codes = self.retriever.candidate_codes("The quarterly budget meeting is on Tuesday")
        self.assertEqual(len(codes), 0)


if __name__ == "__main__":
    unittest.main()
