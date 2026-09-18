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

## Anti-patterns to reject in review

- A dict mapping symptom phrases to ICD codes.
- A regex over guideline text for "must", "should not", "excludes".
- Any special case named after a code we happened to see while testing.
