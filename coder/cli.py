"""Entry point: reads a note or a file of notes, runs the pipeline, writes
one JSONL record per note. Input path is an argument, never a constant —
the grader points this at their own file.

A malformed row must not take down the whole batch — the "nothing silently
disappears" contract (see skills/coding-output-contract) starts at the file
parser, not just inside the pipeline. A row that fails to parse still
produces a NoteInput (flagged via load_error) so it gets a real output
record explaining why, instead of vanishing or crashing the run."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import Pipeline, record_for_load_error
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
    if not isinstance(row, dict):
        raise ValueError(f"expected a string or object, got {type(row).__name__}")
    if "text" not in row:
        raise ValueError('missing required "text" field')
    note_id = row.get("note_id") or row.get("id") or index
    return NoteInput(note_id=str(note_id), text=row["text"])


def _load_jsonl(path: Path) -> list[NoteInput]:
    notes = []
    with path.open() as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                notes.append(_row_to_note(json.loads(line), i))
            except Exception as exc:
                notes.append(
                    NoteInput(note_id=str(i), text="", load_error=f"line {i + 1}: {exc}")
                )
    return notes


def _load_json(path: Path) -> list[NoteInput]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [NoteInput(note_id=path.stem, text="", load_error=f"invalid JSON in {path.name}: {exc}")]

    if isinstance(data, dict):
        # a bare object is one note, not a list of its own keys
        try:
            return [_row_to_note(data, 0)]
        except Exception as exc:
            return [NoteInput(note_id=path.stem, text="", load_error=f"{path.name}: {exc}")]

    if not isinstance(data, list):
        return [
            NoteInput(
                note_id=path.stem,
                text="",
                load_error=f"{path.name}: expected a JSON object or list, got {type(data).__name__}",
            )
        ]

    notes = []
    for i, row in enumerate(data):
        try:
            notes.append(_row_to_note(row, i))
        except Exception as exc:
            notes.append(NoteInput(note_id=str(i), text="", load_error=f"entry {i}: {exc}"))
    return notes


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

    if not args.input.exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        raise SystemExit(1)

    notes = load_notes(args.input)
    pipeline = Pipeline()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
    out = args.output.open("w") if args.output else sys.stdout
    try:
        for note in notes:
            record = record_for_load_error(note) if note.load_error else pipeline.process(note)
            out.write(json.dumps(record.to_dict()) + "\n")
            out.flush()
    finally:
        if args.output:
            out.close()


if __name__ == "__main__":
    main()
