---
name: clinical-retrieval
description: "How to retrieve candidate ICD-11 codes and guideline snippets for a free-text consult note in this project, without keyword tables or regex matching that would overfit to notes we've seen."
---

# Clinical evidence retrieval

Used whenever writing or changing the retrieval step of the coding pipeline
(matching a note against `data/icd_catalog.json` and
`data/guideline_snippets.json`, plus any additions).

## Ground rule

The grading notes are never seen in advance. Anything keyed to a specific
phrase, keyword list, or regex over "should not" / "contraindicated" etc.
will overfit and silently fail on different wording. Retrieval must be a
general similarity/reasoning method, not a lookup table.

## Approach

1. **Statistical retrieval as the candidate generator**, not the decision
   maker. Use a vector-similarity method (TF-IDF + cosine, or embeddings if a
   model/key is available) over:
   - catalog: `title` + `synonyms` per code
   - guidelines: `title` + `text` per snippet
   against the note text. Pull top-K (e.g. 8-10) candidates from each corpus.
   This must work with **zero API key** — it's the fallback path too, so it
   cannot depend on an external embedding call.
2. **Never filter guidelines by keyword before ranking.** A restriction is
   often a subordinate clause with no signal word. Rank *all* 45(+) snippets
   by similarity to the note (and to each retrieved candidate code's
   title/chapter), don't pre-screen by string match.
3. **Retrieve guidelines against the candidate code, not just the note.**
   A guideline that qualifies "when to assign this code" may share little
   vocabulary with the note itself. Run a second retrieval pass keyed to each
   top candidate code's title/chapter/synonyms, and union the results.
4. **Chapter/context signal is retrieval evidence, not a rule.** If the note
   implies an age, sex, acuity or setting, that's just another feature the
   retrieval and reasoning step reasons over — don't hardcode an age-band
   filter.
5. **Cap candidates fed to the reasoning step** (e.g. top 5 codes, top 8
   guidelines) so the LLM/deterministic reasoner sees a tractable set, but
   log what was cut so the "what would raise confidence" field can mention it.
6. **No match above threshold → say so.** If nothing clears a similarity
   floor, that's retrieval evidence for a refusal, not a reason to force the
   top-1 result through.
7. **Expand fixed clinical shorthand before tokenizing** (`coder/
   abbreviations.py`) — a real note written as "pt c/o SOB, JVP raised,
   bibasal creps" shares almost no vocabulary with a catalogue written in
   full clinical English, and lexical retrieval can miss a code that's
   plainly in the catalogue purely because of how the note abbreviates it.
   This is a fixed, standard-vocabulary normalisation, not a diagnosis
   lookup — the abbreviation list is closed and reviewed the same way a
   stopword list would be, never grown to special-case one note.
8. **Widen the query with the extractor's differential terms when a model
   is available** (`ClinicalPicture.differential_terms`, wired in
   `pipeline.py`). Lexical retrieval can score exactly zero for a code that
   shares no vocabulary with the note at all — "worst headache of my life"
   and "subarachnoid haemorrhage" have no words in common — even though the
   catalogue entry exists. Confirmed empirically: `8B02` (subarachnoid
   haemorrhage) doesn't appear even in the top 25 candidates for a
   textbook thunderclap-headache note on note-text alone. This gap can't be
   closed by widening top-K (it's a true zero-similarity case, not a
   ranking problem) or by a keyword table (that's exactly the anti-pattern
   below) — it needs the reasoning step that already runs once per note to
   name a few clinically-plausible search terms, including a dangerous one
   worth ruling out even if the note's own words never point at it. This
   only helps in the keyed path; the no-key floor stays lexical-only.

## A known, accepted limitation

Chapter names are indexed alongside title/synonyms because they're
sometimes the only shared vocabulary (e.g. a note describing a psychiatric
presentation and a mental-health chapter title). The cost: a chapter title
containing a generic word ("Symptoms, signs or clinical findings") can
create a weak spurious match whenever a note happens to use that same
generic word for unrelated reasons (a note saying "no other symptoms"
scored against every Chapter 21 entry). A stopword filter
(`coder/tfidf.py`) removes pure function-word noise but deliberately leaves
real content words like "symptoms" alone — they're not noise in general,
just noise in this one shape of case. This is left as retrieval's
imprecision on purpose: the per-candidate agent's job (see
[[agent-architecture]]) is to independently judge whether a retrieved
candidate is actually supported, precisely so retrieval doesn't have to be
perfect for the system as a whole to be safe. A weak candidate reaching the
reasoning layer and getting correctly rejected there is fine; a strong
candidate never reaching it at all (see point 8 above) is the failure mode
that actually matters.

## Anti-patterns to reject in review

- A dict mapping symptom phrases to ICD codes.
- A regex over guideline text for "must", "should not", "excludes".
- Any special case named after a code we happened to see while testing.
- Growing `coder/abbreviations.py` to include a phrase specific to one note
  rather than a genuinely standard, widely-used piece of clinical shorthand.
