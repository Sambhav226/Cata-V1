"""A malformed row in the input file must not take down the whole batch —
this is the "nothing silently disappears" contract applied to the file
parser itself, not just the pipeline. See skills/coding-output-contract."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from coder.cli import load_notes


class CliRobustnessTest(unittest.TestCase):
    def _write(self, name: str, content: str) -> Path:
        d = Path(tempfile.mkdtemp())
        p = d / name
        p.write_text(content)
        return p

    def test_bad_jsonl_line_isolated_not_batch_failure(self):
        path = self._write(
            "notes.jsonl",
            '{"note_id": "1", "text": "ok note"}\n'
            "42\n"  # valid JSON, wrong shape
            '{"note_id": "3"}\n'  # missing text
            '{"note_id": "4", "text": "another ok note"}\n',
        )
        notes = load_notes(path)
        self.assertEqual(len(notes), 4)
        self.assertIsNone(notes[0].load_error)
        self.assertIsNotNone(notes[1].load_error)
        self.assertIsNotNone(notes[2].load_error)
        self.assertIsNone(notes[3].load_error)

    def test_json_dict_treated_as_single_note_not_corrupted(self):
        path = self._write("notes.json", json.dumps({"note_id": "a", "text": "ok note"}))
        notes = load_notes(path)
        self.assertEqual(len(notes), 1)
        self.assertIsNone(notes[0].load_error)
        self.assertEqual(notes[0].text, "ok note")

    def test_json_dict_without_text_reports_error_not_crash(self):
        path = self._write("notes.json", json.dumps({"note_id": "a"}))
        notes = load_notes(path)
        self.assertEqual(len(notes), 1)
        self.assertIsNotNone(notes[0].load_error)

    def test_empty_json_file_does_not_crash(self):
        path = self._write("notes.json", "")
        notes = load_notes(path)
        self.assertEqual(len(notes), 1)
        self.assertIsNotNone(notes[0].load_error)

    def test_json_list_with_one_bad_entry_isolated(self):
        path = self._write(
            "notes.json",
            json.dumps([{"note_id": "1", "text": "ok"}, {"note_id": "2"}, "plain string note"]),
        )
        notes = load_notes(path)
        self.assertEqual(len(notes), 3)
        self.assertIsNone(notes[0].load_error)
        self.assertIsNotNone(notes[1].load_error)
        self.assertIsNone(notes[2].load_error)


if __name__ == "__main__":
    unittest.main()
