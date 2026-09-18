---
name: coding-output-contract
description: "The required output shape and refusal discipline for every note the clinical coding pipeline processes — use when writing the reasoning/output step or output schema/tests."
---

# Coding output contract

Used whenever writing, changing, or testing the final output stage of the
pipeline (the thing that turns a decision into the record we emit per note).

## Every note gets exactly one output record. No exceptions.

A note that errors, times out, has no API key available, or matches nothing
still produces a record. Nothing is dropped, skipped, or crashes the batch
run. If something in the pipeline throws, catch it at the per-note boundary
and emit an unresolved record with the error reason, then continue to the
next note.

## Required fields per record

- `note_id` (or index if the input has none)
- `codes`: list of `{code, title, confidence_contribution}` — empty list is
  valid and expected when refusing
- `refusal`: `{refused: bool, reason: str|null}` — explicit, not inferred
  from an empty `codes` list
- `evidence`: `{catalog_codes_cited: [...], guideline_ids_cited: [...]}` —
  every code/guideline that materially affected the decision, including ones
  that ruled something *out*
- `confidence`: `{level: high|medium|low, would_raise: str, would_lower: str}`
  — `would_raise`/`would_lower` must be specific to this note (e.g. "a
  documented organism" not "more information")
- `unresolved`: list of strings — anything in the note the system could not
  place, plus anything (like a guideline conflict) it noticed but couldn't
  settle. Empty list is valid.

## Refusal discipline

- **No confident retrieval match → refuse, don't force the nearest code.**
  The brief scores refusal above a plausible-looking guess. A near-miss
  candidate belongs in `unresolved` with why it didn't clear the bar, not in
  `codes`.
- **A condition the catalog plainly doesn't carry → say that explicitly** in
  `refusal.reason`, don't silently pick the closest chapter.
- **No API key present** is not an error state for the run — it's a reason
  individual notes fall through to the deterministic path or land in
  `unresolved` if that path can't resolve them. The run must still complete
  and emit a record for every note.

## Multi-code notes

A note can produce more than one code (e.g. a symptom plus an unrelated
finding). Don't force single-code output; don't over-split a single
condition into redundant codes either — GDL-001-style "symptom folds into
the established diagnosis" reasoning applies here too (see
[[guideline-conflicts]]).

## Testing this contract

Any test suite must assert: N notes in → N records out (even with malformed
input, an empty note, or no API key set), and that a forced-error note still
yields a valid record instead of killing the batch.
