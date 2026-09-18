"""Turns raw note text into a structured, phrasing-independent clinical
picture. Never proposes a code — see skills/agent-architecture."""
from __future__ import annotations

from .. import llm
from ..schemas import ClinicalPicture

_SYSTEM = """You read a free-text outpatient consult note written by a clinical \
officer at a district hospital. Extract the clinical picture as structured \
JSON. Do not diagnose, do not propose a code, and do not infer anything the \
note does not support. Respond with only a JSON object with these keys: \
complaint (string), findings (array of strings — exam/lab/history facts \
actually stated), duration_or_onset (string or null), stated_diagnosis \
(string or null, only if the clinician wrote one explicitly), \
notable_absences (array of strings — clinically relevant information a \
coder would want that this note does not provide, e.g. no organism named, \
no duration given)."""


def extract(note_text: str) -> ClinicalPicture:
    result = llm.complete_json(_SYSTEM, note_text)
    if result is None:
        return _fallback(note_text)
    try:
        return ClinicalPicture(
            complaint=result.get("complaint") or "",
            findings=list(result.get("findings") or []),
            duration_or_onset=result.get("duration_or_onset"),
            stated_diagnosis=result.get("stated_diagnosis"),
            notable_absences=list(result.get("notable_absences") or []),
            raw_note=note_text,
        )
    except Exception:
        return _fallback(note_text)


def _fallback(note_text: str) -> ClinicalPicture:
    """No model available: pass the raw note through unstructured. The
    candidate/adjudicator fallbacks don't depend on structure being present."""
    return ClinicalPicture(
        complaint=note_text.strip()[:200],
        findings=[],
        duration_or_onset=None,
        stated_diagnosis=None,
        notable_absences=["no model available to structure this note"],
        raw_note=note_text,
    )
