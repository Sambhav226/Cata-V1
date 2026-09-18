---
name: data-expansion
description: "How to add real ICD-11 codes or guideline material to close gaps found in data/icd_catalog.json and data/guideline_snippets.json, so additions stay cited and legible in the diff."
---

# Expanding the catalogue and corpus

Used when the retrieval/reasoning work surfaces a real presentation or a
real restriction that the supplied 404 codes or 45 guidelines don't cover.

## Ground rule

The supplied data is a starting set, not ground truth. Only ~404 codes and
45 snippets exist; real outpatient presentations will fall outside it. The
brief specifically scores whether we went looking for gaps and closed them —
but additions must stay separate and cited, never merged silently into the
originals.

## Where additions live

- `data/icd_catalog_additions.json` — same schema as `icd_catalog.json`
  (`code`, `title`, `chapter`, `synonyms`), plus a `source` field per entry
  (e.g. WHO ICD-11 browser URL/ID, or a maintained ICD-11 index release).
- `data/guideline_additions.json` — same schema as `guideline_snippets.json`
  (`id` prefixed distinctly, e.g. `ADD-001`, `title`, `source`, `effective`,
  `text`), `source` pointing to where the real guidance came from.
- The loader reads both original + additions files and merges them at
  runtime — the originals on disk are never edited in place.

## When to add something

- A candidate presentation shows up during testing/dev (not from the hidden
  grading notes — we never see those) that has no reasonable catalogue entry
  and *should*, given the scope of an outpatient district-hospital setting.
- A retrieval/reasoning gap where real coding guidance exists (specificity
  rules, exclusion criteria, age/duration prerequisites) that the 45
  snippets don't cover, and the gap would matter for correctness.

## What each addition needs

1. A real source — don't fabricate a plausible-sounding code or guideline
   text. Cite where it came from (ICD-11 release, coding manual, WHO
   guidance).
2. A one-line note in the README's "what we added and why" section: the gap,
   why it was worth closing, and the source.
3. Kept out of the original two files so the diff between supplied data and
   added data stays legible to the grader.

## Anti-pattern to reject in review

- Inventing a code or guideline snippet with no real source to patch a test
  case — this is exactly the "confidently wrong" failure mode the brief
  warns is worse than a rejected claim.

## If a supplied entry looks wrong, not just missing

Verifying real additions against WHO ICD-11 sources can surface a supplied
entry that's itself mislabeled — e.g. `1E50` in `data/icd_catalog.json` is
titled "Human immunodeficiency virus disease," but the real ICD-11 code for
HIV disease is `1C60`–`1C62`; real `1E50` is acute viral hepatitis. Don't
"fix" the supplied file — it's graded as given and the brief wants the
diff legible, not a silent correction. Name it in the README instead, as
direct evidence the supplied data isn't ground truth.
