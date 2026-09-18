"""Two-corpus retriever: candidate ICD codes, and guidelines retrieved both
against the raw note and against each candidate code. A restriction often
shares no vocabulary with the note itself, only with the code it restricts
— see skills/clinical-retrieval."""
from __future__ import annotations

from .data import load_catalog, load_guidelines
from .schemas import CatalogEntry, GuidelineEntry, RetrievedCode, RetrievedGuideline
from .tfidf import TfidfIndex

CODE_SIMILARITY_FLOOR = 0.08


class Retriever:
    def __init__(
        self,
        catalog: list[CatalogEntry] | None = None,
        guidelines: list[GuidelineEntry] | None = None,
    ):
        self.catalog = catalog if catalog is not None else load_catalog()
        self.guidelines = guidelines if guidelines is not None else load_guidelines()
        self._code_index = TfidfIndex(
            [f"{e.title} {' '.join(e.synonyms)} {e.chapter}" for e in self.catalog]
        )
        self._guideline_index = TfidfIndex(
            [f"{g.title} {g.text}" for g in self.guidelines]
        )

    def candidate_codes(self, note_text: str, top_k: int = 6) -> list[RetrievedCode]:
        hits = self._code_index.query(note_text, top_k)
        return [
            RetrievedCode(entry=self.catalog[i], score=score)
            for i, score in hits
            if score >= CODE_SIMILARITY_FLOOR
        ]

    def candidate_guidelines(
        self,
        note_text: str,
        codes: list[RetrievedCode],
        top_k_note: int = 8,
        top_k_per_code: int = 4,
    ) -> list[RetrievedGuideline]:
        best: dict[str, RetrievedGuideline] = {}

        def consider(idx: int, score: float) -> None:
            g = self.guidelines[idx]
            current = best.get(g.id)
            if current is None or score > current.score:
                best[g.id] = RetrievedGuideline(entry=g, score=score)

        for idx, score in self._guideline_index.query(note_text, top_k_note):
            consider(idx, score)

        for code in codes:
            query = f"{code.entry.title} {' '.join(code.entry.synonyms)} {code.entry.chapter}"
            for idx, score in self._guideline_index.query(query, top_k_per_code):
                consider(idx, score)

        return sorted(best.values(), key=lambda rg: rg.score, reverse=True)
