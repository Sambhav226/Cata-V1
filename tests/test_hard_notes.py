"""A harder, deliberately out-of-distribution note set — very different
from tests/fixtures/sample_notes.jsonl — used to stress-test retrieval and
the output contract on notes never used to tune anything. This is the
generalisation audit that motivated coder/abbreviations.py, the stopword
filter in coder/tfidf.py, and ClinicalPicture.differential_terms: see
README.md "What survives a different set of notes" for what it found.

Assertions here are structural (contract, no-crash, "retrieval found
something plausible"), never exact-code-match — pinning an exact code would
be the same overfitting-to-phrasing mistake the whole project argues
against, just moved into the test suite."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coder.cli import load_notes
from coder.pipeline import Pipeline

FIXTURE = Path(__file__).parent / "fixtures" / "hard_notes.jsonl"


class HardNotesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notes = load_notes(FIXTURE)
        cls.pipeline = Pipeline()
        cls.records = {n.note_id: cls.pipeline.process(n) for n in cls.notes}

    def test_every_note_produces_exactly_one_valid_record(self):
        self.assertEqual(len(self.records), len(self.notes))
        for record in self.records.values():
            d = record.to_dict()
            for key in ("note_id", "codes", "refusal", "evidence", "confidence", "unresolved"):
                self.assertIn(key, d)

    def test_notes_with_a_plausible_catalogue_match_retrieve_something(self):
        # these describe presentations the catalogue plainly carries
        # (including two of the additions) — retrieval should surface at
        # least one candidate for the no-key fallback to cite, even though
        # it still refuses without a model to weigh them.
        for note_id in ("chest-pain-regression", "vivax-malaria", "covid-suspected"):
            cited = self.records[note_id].evidence.catalog_codes_cited
            self.assertTrue(cited, f"{note_id}: expected at least one retrieved candidate, got none")

    def test_injected_directive_does_not_smuggle_its_target_code_through(self):
        # the note literally contains the string "BA41" inside a fake
        # directive; retrieval must not treat a code string mentioned in
        # note text as a match target (codes aren't part of the indexed
        # text), and the no-key path must never assign a code regardless.
        record = self.records["injection-in-note"]
        self.assertNotIn("BA41", record.evidence.catalog_codes_cited)
        self.assertEqual(record.codes, [])

    def test_no_note_crashes_regardless_of_shape(self):
        # long rambling text, heavy clinical shorthand, an embedded fake
        # directive, and a minimal one-line note are all in the fixture —
        # none of them should have raised getting here at all, but assert
        # every record is still a refusal-or-codes-consistent record.
        for record in self.records.values():
            if record.codes:
                self.assertFalse(record.refusal.refused)
            else:
                self.assertTrue(record.refusal.refused)


if __name__ == "__main__":
    unittest.main()
