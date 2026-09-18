"""Contract test: N notes in, N records out, never a crash, even with no
API key set. See skills/coding-output-contract."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coder.pipeline import Pipeline
from coder.schemas import NoteInput


class ContractTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.pipeline = Pipeline()

    def test_every_note_produces_one_valid_record(self):
        notes = [
            NoteInput(note_id="1", text="Three days of watery diarrhoea, no blood, no fever."),
            NoteInput(note_id="2", text=""),
            NoteInput(note_id="3", text="Routine follow-up, no new complaints."),
        ]
        records = [self.pipeline.process(n) for n in notes]
        self.assertEqual(len(records), len(notes))
        for record in records:
            d = record.to_dict()
            for key in ("note_id", "codes", "refusal", "evidence", "confidence", "unresolved"):
                self.assertIn(key, d)

    def test_empty_note_does_not_crash(self):
        record = self.pipeline.process(NoteInput(note_id="empty", text=""))
        self.assertEqual(record.note_id, "empty")

    def test_no_key_path_never_guesses(self):
        record = self.pipeline.process(
            NoteInput(note_id="x", text="Patient has bacillary dysentery symptoms")
        )
        # without a model, the fallback path must not assign a code outright
        self.assertEqual(record.codes, [])


if __name__ == "__main__":
    unittest.main()
