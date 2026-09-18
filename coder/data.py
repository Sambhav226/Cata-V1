"""Loads the ICD catalogue and guideline corpus, merging the supplied files
with any sourced additions. The supplied files are never edited in place —
see skills/data-expansion for where additions live and why."""
from __future__ import annotations

import json
from pathlib import Path

from .schemas import CatalogEntry, GuidelineEntry

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def load_catalog(data_dir: Path = DATA_DIR) -> list[CatalogEntry]:
    rows = _load_json(data_dir / "icd_catalog.json") + _load_json(
        data_dir / "icd_catalog_additions.json"
    )
    return [
        CatalogEntry(
            code=row["code"],
            title=row["title"],
            chapter=row.get("chapter", ""),
            synonyms=row.get("synonyms", []),
            source=row.get("source"),
        )
        for row in rows
    ]


def load_guidelines(data_dir: Path = DATA_DIR) -> list[GuidelineEntry]:
    rows = _load_json(data_dir / "guideline_snippets.json") + _load_json(
        data_dir / "guideline_additions.json"
    )
    return [
        GuidelineEntry(
            id=row["id"],
            title=row["title"],
            source=row.get("source", ""),
            effective=row.get("effective", ""),
            text=row["text"],
        )
        for row in rows
    ]
