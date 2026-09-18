"""Shared data contracts for the coding pipeline. Plain dataclasses, not
pydantic — the corpus and schemas here are small enough that a validation
framework would be dead weight."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class NoteInput:
    note_id: str
    text: str


@dataclass
class CatalogEntry:
    code: str
    title: str
    chapter: str
    synonyms: list[str] = field(default_factory=list)
    source: Optional[str] = None


@dataclass
class GuidelineEntry:
    id: str
    title: str
    source: str
    effective: str
    text: str


@dataclass
class RetrievedCode:
    entry: CatalogEntry
    score: float


@dataclass
class RetrievedGuideline:
    entry: GuidelineEntry
    score: float


@dataclass
class ClinicalPicture:
    """Extractor output: a structured, phrasing-independent read of the
    note. Deliberately does not propose a code — see
    skills/agent-architecture."""

    complaint: str
    findings: list[str]
    duration_or_onset: Optional[str]
    stated_diagnosis: Optional[str]
    notable_absences: list[str]
    raw_note: str


@dataclass
class CandidateVerdict:
    code: str
    title: str
    supports: bool
    confidence: float
    supporting_evidence: list[str]
    disqualifying_evidence: list[str]
    reasoning: str


@dataclass
class ConflictFinding:
    description: str
    guideline_ids: list[str]
    resolved: bool
    resolution: Optional[str]


@dataclass
class Confidence:
    level: str
    would_raise: str
    would_lower: str


@dataclass
class ProposedCode:
    code: str
    title: str
    confidence_contribution: float


@dataclass
class Refusal:
    refused: bool
    reason: Optional[str]


@dataclass
class Evidence:
    catalog_codes_cited: list[str]
    guideline_ids_cited: list[str]


@dataclass
class CodingRecord:
    note_id: str
    codes: list[ProposedCode]
    refusal: Refusal
    evidence: Evidence
    confidence: Confidence
    unresolved: list[str]

    def to_dict(self) -> dict:
        return asdict(self)
