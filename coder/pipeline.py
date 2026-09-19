"""Orchestrates the five-agent pipeline per note — see
skills/agent-architecture. One try/except per note: a failure anywhere
yields an unresolved record instead of killing the batch, per
skills/coding-output-contract."""
from __future__ import annotations

import concurrent.futures
import traceback

from .agents import adjudicator, auditor, candidate, extractor
from .retrieval import Retriever
from .schemas import CodingRecord, Confidence, Evidence, NoteInput, Refusal

MAX_CANDIDATES = 5


class Pipeline:
    def __init__(self, retriever: Retriever | None = None):
        self.retriever = retriever or Retriever()

    def process(self, note: NoteInput) -> CodingRecord:
        try:
            return self._process(note)
        except Exception as exc:  # per-note isolation is the point, not a bug
            return _error_record(note, exc)

    def _process(self, note: NoteInput) -> CodingRecord:
        picture = extractor.extract(note.text)

        # Widen the retrieval query with the extractor's differential terms
        # when available (real model only — the no-key fallback never
        # populates this). Plain lexical retrieval on the note text alone
        # can score zero for a code that shares no vocabulary with the note
        # at all (e.g. "worst headache of my life" vs. "subarachnoid
        # haemorrhage") even though the catalogue entry exists — see
        # skills/clinical-retrieval.
        retrieval_query = note.text
        if picture.differential_terms:
            retrieval_query = f"{note.text} {' '.join(picture.differential_terms)}"

        codes = self.retriever.candidate_codes(retrieval_query, top_k=MAX_CANDIDATES)
        if not codes:
            return CodingRecord(
                note_id=note.note_id,
                codes=[],
                refusal=Refusal(
                    refused=True,
                    reason="no catalogue entry retrieved above the similarity floor for this note",
                ),
                evidence=Evidence(catalog_codes_cited=[], guideline_ids_cited=[]),
                confidence=Confidence(
                    level="low",
                    would_raise="a catalogue entry matching this presentation",
                    would_lower="n/a — already refusing",
                ),
                unresolved=["no plausible ICD-11 code found in the catalogue for this note"],
            )

        guidelines = self.retriever.candidate_guidelines(retrieval_query, codes)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(codes) + 1) as pool:
            verdict_futures = [pool.submit(candidate.evaluate, picture, c, guidelines) for c in codes]
            audit_future = pool.submit(auditor.audit, picture, guidelines, codes)
            verdicts = [f.result() for f in verdict_futures]
            conflicts = audit_future.result()

        return adjudicator.decide(note.note_id, picture, verdicts, conflicts)


def _error_record(note: NoteInput, exc: Exception) -> CodingRecord:
    return CodingRecord(
        note_id=note.note_id,
        codes=[],
        refusal=Refusal(refused=True, reason=f"pipeline error: {exc}"),
        evidence=Evidence(catalog_codes_cited=[], guideline_ids_cited=[]),
        confidence=Confidence(level="low", would_raise="n/a", would_lower="n/a"),
        unresolved=[
            f"unhandled error, note not processed: {exc}",
            traceback.format_exc(limit=3),
        ],
    )


def record_for_load_error(note: NoteInput) -> CodingRecord:
    """A row that failed to parse in the input file still gets a real
    record instead of vanishing — see skills/coding-output-contract."""
    return CodingRecord(
        note_id=note.note_id,
        codes=[],
        refusal=Refusal(refused=True, reason=f"input row could not be parsed: {note.load_error}"),
        evidence=Evidence(catalog_codes_cited=[], guideline_ids_cited=[]),
        confidence=Confidence(level="low", would_raise="n/a", would_lower="n/a"),
        unresolved=[f"input row malformed, not processed: {note.load_error}"],
    )
