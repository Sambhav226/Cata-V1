"""The only agent allowed to write the final CodingRecord. Must cite what
the other agents found rather than re-deriving evidence — see
skills/agent-architecture and skills/coding-output-contract."""
from __future__ import annotations

from .. import llm
from ..schemas import (
    CandidateVerdict,
    ClinicalPicture,
    CodingRecord,
    Confidence,
    ConflictFinding,
    Evidence,
    ProposedCode,
    Refusal,
)

_SYSTEM = """You are the final decision-maker assigning ICD-11 code(s) to an \
outpatient consult note, or refusing. You are given: the extracted clinical \
picture, an independent verdict from a dedicated reviewer for each \
candidate code, and a conflict audit of the retrieved guidelines. Base your \
decision ONLY on what these sub-reviews surfaced — do not introduce new \
reasoning they did not raise. A refusal is scored above a plausible-but-\
unsupported guess: if no candidate is well supported, or the catalogue \
plainly doesn't carry this condition, refuse and say why. A note can \
produce zero, one, or multiple codes. Respond with only a JSON object: \
codes (array of {code, title, confidence_contribution 0-1}), refused \
(boolean), refusal_reason (string or null), catalog_codes_cited (array of \
code strings), guideline_ids_cited (array of id strings), confidence_level \
("high"|"medium"|"low"), would_raise (string, specific to this note), \
would_lower (string, specific to this note), unresolved (array of strings \
— anything in the note you could not place, plus any unresolved conflict \
from the audit)."""


def decide(
    note_id: str,
    picture: ClinicalPicture,
    verdicts: list[CandidateVerdict],
    conflicts: list[ConflictFinding],
) -> CodingRecord:
    result = llm.complete_json(_SYSTEM, _build_prompt(picture, verdicts, conflicts))
    if result is None:
        return _fallback(note_id, verdicts, conflicts)
    try:
        return CodingRecord(
            note_id=note_id,
            codes=[
                ProposedCode(
                    code=c["code"],
                    title=c.get("title", ""),
                    confidence_contribution=float(c.get("confidence_contribution", 0.0)),
                )
                for c in (result.get("codes") or [])
            ],
            refusal=Refusal(
                refused=bool(result.get("refused", False)),
                reason=result.get("refusal_reason"),
            ),
            evidence=Evidence(
                catalog_codes_cited=list(result.get("catalog_codes_cited") or []),
                guideline_ids_cited=list(result.get("guideline_ids_cited") or []),
            ),
            confidence=Confidence(
                level=result.get("confidence_level", "low"),
                would_raise=result.get("would_raise", ""),
                would_lower=result.get("would_lower", ""),
            ),
            unresolved=list(result.get("unresolved") or []),
        )
    except Exception:
        return _fallback(note_id, verdicts, conflicts)


def _build_prompt(
    picture: ClinicalPicture, verdicts: list[CandidateVerdict], conflicts: list[ConflictFinding]
) -> str:
    verdict_block = "\n".join(
        f"- {v.code} {v.title}: supports={v.supports} confidence={v.confidence:.2f} "
        f"for={v.supporting_evidence} against={v.disqualifying_evidence} :: {v.reasoning}"
        for v in verdicts
    )
    conflict_block = "\n".join(
        f"- {c.description} [{', '.join(c.guideline_ids)}] resolved={c.resolved} {c.resolution or ''}"
        for c in conflicts
    ) or "(none retrieved)"
    return (
        f"PICTURE:\ncomplaint: {picture.complaint}\nfindings: {picture.findings}\n"
        f"duration_or_onset: {picture.duration_or_onset}\n"
        f"stated_diagnosis: {picture.stated_diagnosis}\n"
        f"notable_absences: {picture.notable_absences}\n\n"
        f"CANDIDATE VERDICTS:\n{verdict_block}\n\n"
        f"CONFLICT AUDIT:\n{conflict_block}"
    )


def _fallback(
    note_id: str, verdicts: list[CandidateVerdict], conflicts: list[ConflictFinding]
) -> CodingRecord:
    """No model available: never guess. The fallback path leans toward
    unresolved, not toward a decision — see skills/agent-architecture."""
    unresolved = ["no model available to adjudicate between candidates"]
    unresolved += [c.description for c in conflicts if not c.resolved]
    return CodingRecord(
        note_id=note_id,
        codes=[],
        refusal=Refusal(
            refused=True,
            reason="no model available; retrieval similarity alone is not a sufficient basis to assign a code",
        ),
        evidence=Evidence(
            catalog_codes_cited=[v.code for v in verdicts],
            guideline_ids_cited=[],
        ),
        confidence=Confidence(
            level="low",
            would_raise="a configured model to weigh the retrieved guidelines against each candidate",
            would_lower="n/a — already refusing",
        ),
        unresolved=unresolved,
    )
