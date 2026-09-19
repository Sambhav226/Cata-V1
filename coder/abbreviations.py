"""Expands common clinical shorthand before a note reaches TF-IDF retrieval.

This is a fixed, standard vocabulary normalisation (SOB -> shortness of
breath), not a diagnosis lookup table — see skills/clinical-retrieval. It
exists because a real consult note written in a hurry ("pt c/o SOB x2/7,
JVP raised, bibasal creps") shares almost no vocabulary with a catalogue
written in full clinical English, so retrieval can miss a code that's
plainly in the catalogue purely because of how the note abbreviates it.
This does not fix retrieval finding a code from a symptom *cluster* it was
never told the name of (see ClinicalPicture.differential_terms in
schemas.py for that harder problem) — it only recovers vocabulary that was
already there, just abbreviated."""
from __future__ import annotations

import re

# Deliberately small and conservative: standard, widely-used shorthand only,
# not an attempt to cover every possible abbreviation. False expansions are
# worse than a missed one, so ambiguous short forms ("MI" could be several
# things depending on context) are left out.
_ABBREVIATIONS = {
    "sob": "shortness of breath",
    "sob's": "shortness of breath",
    "c/o": "complains of",
    "pmhx": "past medical history",
    "pmh": "past medical history",
    "hx": "history",
    "dx": "diagnosis",
    "tx": "treatment",
    "rx": "prescription treatment",
    "fx": "fracture",
    "htn": "hypertension",
    "dm": "diabetes mellitus",
    "t2dm": "type 2 diabetes mellitus",
    "copd": "chronic obstructive pulmonary disease",
    "uti": "urinary tract infection",
    "uri": "upper respiratory infection",
    "gi": "gastrointestinal",
    "gu": "genitourinary",
    "jvp": "jugular venous pressure",
    "pnd": "paroxysmal nocturnal dyspnoea",
    "creps": "crepitations",
    "crep": "crepitations",
    "n/v": "nausea and vomiting",
    "loc": "loss of consciousness",
    "abx": "antibiotics",
    "bpm": "beats per minute",
    "cva": "cerebrovascular accident stroke",
    "tia": "transient ischaemic attack",
    "pe": "pulmonary embolism",
    "dvt": "deep vein thrombosis",
    "ams": "altered mental status",
    "wbc": "white blood cell",
    "afib": "atrial fibrillation",
    "chf": "congestive heart failure",
    "ckd": "chronic kidney disease",
    "aki": "acute kidney injury",
    "gerd": "gastro-oesophageal reflux disease",
    "iud": "intrauterine device",
    "ors": "oral rehydration solution",
}

_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in sorted(_ABBREVIATIONS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def expand(text: str) -> str:
    """Appends the expansion after each abbreviation found rather than
    replacing it, so retrieval sees both the shorthand and the full term."""
    def _replace(match: re.Match) -> str:
        key = match.group(0).lower()
        expansion = _ABBREVIATIONS.get(key)
        return f"{match.group(0)} {expansion}" if expansion else match.group(0)

    return _PATTERN.sub(_replace, text)
