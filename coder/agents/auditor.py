"""Reads all retrieved guidelines together, hunting for unannounced
restrictions and guideline-vs-guideline contradiction — see
skills/guideline-conflicts. Runs independently of the candidate agents so
tension-finding isn't diluted into a single code's evaluation."""
from __future__ import annotations

from .. import llm
from ..schemas import ClinicalPicture, ConflictFinding, RetrievedGuideline

_SYSTEM = """You audit a set of clinical coding guideline snippets pulled \
for one consult note. Two failure modes to catch: (1) a restriction hiding \
in ordinary prose — a definition, scope statement, prerequisite, age band, \
or temporal window that narrows or overrides another snippet, stated with \
no signal word; (2) two snippets that genuinely conflict, or one supersedes \
the other (prefer the more specific snippet for the same situation; if \
specificity is equal, prefer the more recent effective date; if neither \
resolves it, say so). This corpus has been migrated and edited over years — \
treat it as a real, imperfect document library, not ground truth. Respond \
with only a JSON object: findings (array of objects with description, \
guideline_ids (array), resolved (boolean), resolution (string or null — \
required if resolved is true, state the resolution rule used))."""


def audit(picture: ClinicalPicture, guidelines: list[RetrievedGuideline]) -> list[ConflictFinding]:
    if not guidelines:
        return []
    result = llm.complete_json(_SYSTEM, _build_prompt(picture, guidelines))
    if result is None:
        return _fallback()
    try:
        return [
            ConflictFinding(
                description=str(row.get("description", "")),
                guideline_ids=list(row.get("guideline_ids") or []),
                resolved=bool(row.get("resolved", False)),
                resolution=row.get("resolution"),
            )
            for row in (result.get("findings") or [])
        ]
    except Exception:
        return _fallback()


def _build_prompt(picture: ClinicalPicture, guidelines: list[RetrievedGuideline]) -> str:
    block = "\n".join(
        f"[{g.entry.id}] {g.entry.title} ({g.entry.effective}, {g.entry.source}): {g.entry.text}"
        for g in guidelines
    )
    return f"NOTE COMPLAINT: {picture.complaint}\n\nRETRIEVED GUIDELINES:\n{block}"


def _fallback() -> list[ConflictFinding]:
    return [
        ConflictFinding(
            description="no model available to audit retrieved guidelines for conflicts",
            guideline_ids=[],
            resolved=False,
            resolution=None,
        )
    ]
