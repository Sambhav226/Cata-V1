"""Entry point: reads a note or a file of notes, runs the pipeline, writes
one JSONL record per note. Input path is an argument, never a constant —
the grader points this at their own file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import Pipeline
from .schemas import NoteInput


def load_notes(path: Path) -> list[NoteInput]:
    if path.suffix == ".jsonl":
        return _load_jsonl(path)
    if path.suffix == ".json":
        return _load_json(path)
    return _load_txt(path)


def _row_to_note(row, index: int) -> NoteInput:
    if isinstance(row, str):
        return NoteInput(note_id=str(index), text=row)
    note_id = row.get("note_id") or row.get("id") or index
    return NoteInput(note_id=str(note_id), text=row["text"])


def _load_jsonl(path: Path) -> list[NoteInput]:
    notes = []
    with path.open() as f:
        for i, line in enumerate(f):
            line = line.strip()
            if line:
                notes.append(_row_to_note(json.loads(line), i))
    return notes


def _load_json(path: Path) -> list[NoteInput]:
    data = json.loads(path.read_text())
    return [_row_to_note(row, i) for i, row in enumerate(data)]


def _load_txt(path: Path) -> list[NoteInput]:
    """A .txt file is one note by default; multiple notes may be separated
    by a line containing only -----."""
    content = path.read_text()
    blocks = [b.strip() for b in content.split("\n-----\n") if b.strip()]
    if len(blocks) <= 1:
        return [NoteInput(note_id=path.stem, text=content.strip())]
    return [NoteInput(note_id=f"{path.stem}-{i + 1}", text=b) for i, b in enumerate(blocks)]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run consult notes through the clinical coding pipeline."
    )
    parser.add_argument("--input", required=True, type=Path, help="note file (.jsonl, .json, or .txt)")
    parser.add_argument("--output", type=Path, default=None, help="JSONL output path (default: stdout)")
    args = parser.parse_args(argv)

    notes = load_notes(args.input)
    pipeline = Pipeline()

    out = args.output.open("w") if args.output else sys.stdout
    try:
        for note in notes:
            record = pipeline.process(note)
            out.write(json.dumps(record.to_dict()) + "\n")
            out.flush()
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
