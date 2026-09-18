# Agentic clinical coding

Free-text consult note in, ICD-11 assignment (or a reasoned refusal) out,
with cited evidence.

## Running it

```
docker compose up            # smoke run over the bundled sample notes
./run.sh <input-path> [output-path]   # real run against an arbitrary file
```

`run.sh` mounts your host file into the container and passes it as `--input`
— nothing about the input path is baked into the image. Input can be
`.jsonl` (one `{"note_id", "text"}` object per line — recommended), `.json`
(a list of such objects), or `.txt` (one note, or several separated by a
line containing only `-----`). Output is JSONL, one record per note, in
input order.

Without `ANTHROPIC_API_KEY` set, the pipeline still runs end to end — see
"No-key path" below.

Without Docker: `pip install -r requirements.txt && python -m coder.cli
--input <path> --output <path>`. Tests: `python -m unittest discover -s
tests`.

## Architecture

Five narrow agents instead of one prompt holding the whole decision:

```
note → Extractor → retrieval (stdlib TF-IDF) → candidate agent × N (parallel)
                                              → conflict auditor  (parallel)
                                              → adjudicator → record
```

- **Extractor** reads the note into a structured picture (complaint,
  findings, duration, stated diagnosis, notable absences) and proposes no
  code. This is what keeps everything downstream from matching on the
  note's phrasing instead of its content.
- **Retrieval** is TF-IDF/cosine over the catalogue and guideline corpus,
  written against the standard library — the corpus is ~450 short
  documents, too small to justify numpy/sklearn. Guidelines are retrieved
  twice: once against the note, once against each candidate code, because a
  restriction on a code often shares no vocabulary with the note itself.
- **Candidate agents** run one per retrieved code, in parallel, each blind
  to the other candidates, each required to argue both for and against its
  own code. A single prompt holding all candidates tends to anchor on the
  first plausible one and rationalise past what disqualifies it; isolating
  them forces an independent verdict per code.
- **Conflict auditor** runs in parallel with the candidate agents and reads
  every retrieved guideline together, specifically hunting for restrictions
  with no signal word (a definition, an age band, a prerequisite) and for
  guideline-vs-guideline contradiction.
- **Adjudicator** is the only agent that writes the final record, and is
  instructed to cite only what the other agents surfaced, not introduce new
  reasoning of its own.

Full rationale for each piece lives in `skills/` (`agent-architecture`,
`clinical-retrieval`, `guideline-conflicts`, `coding-output-contract`,
`data-expansion`), written as standing instructions I followed while
building this, not after-the-fact documentation.

## No-key path

Every agent is called through one function (`coder/llm.py`); if no key is
set, that function returns `None` and each agent falls through to a
deterministic fallback. The fallback is deliberately thin, not a second
reasoning engine: retrieval still runs, but nothing gets adjudicated into a
code without a model to weigh the guidelines, so every note refuses with the
retrieved candidates left visible in `unresolved`/`evidence` rather than
being dropped. This matches the brief: the no-key path is expected to be
a floor, not a second system.

## What the data made me decide, and against what

- **Similarity is a candidate generator, never the decision.** Early on the
  temptation is to just threshold TF-IDF score and call it a code. The
  catalogue's `synonyms` field made it clear near-miss codes are common
  (multiple diarrhoeal-disease entries, multiple respiratory entries with
  overlapping vocabulary) — a bare threshold would silently pick the wrong
  one about as often as the right one. That's why there's a dedicated
  per-candidate agent instead of "top-1 above threshold."
- **Decided against a single omnibus reasoning prompt.** Faster to build,
  but it's the shape of thing the brief explicitly warns fails: it invites
  the model to find the easy, signposted restrictions and miss the
  buried ones, because the model already anchored on an answer before it
  finished reading the guidelines.
- **Decided against embeddings/vector DB.** No key is a required path, and
  a 450-document corpus doesn't need one — TF-IDF is deterministic,
  dependency-light, and identical in both the keyed and no-key runs, so the
  retrieval layer isn't a second thing to keep in sync across two code
  paths.

## Guideline conflicts

`GDL-001` (a documented underlying diagnosis absorbs its presenting
symptom's code) is the clearest example of a guideline that silently
overrides another candidate rather than stating a restriction outright —
it reads as a specificity rule, not a "restriction," until you ask whether
it disqualifies a code the retrieval step also surfaced. The conflict
auditor is built around exactly this shape: read for what a snippet rules
out, not for language that announces a rule. I have not hand-verified every
pairwise conflict across all 45 snippets — that's a "next day" item, noted
below.

## What I added, and what's still open

Nothing has been sourced into `data/icd_catalog_additions.json` or
`data/guideline_additions.json` yet — the additions mechanism exists (see
`coder/data.py`, `skills/data-expansion`) and the loader already merges it
transparently, but I have not yet gone looking for real gaps in the 404-code
catalogue against plausible district-hospital presentations. This is the
next thing I'd do with more time, and I'd rather say so than backfill a
plausible-looking addition to look complete.

## What survives a different set of notes, and what won't

Likely to hold: the agent split itself, the no-key refusal-first behaviour,
the per-note error isolation, the TF-IDF retrieval generalising to unseen
phrasing (it's tested against a synonym, not a title, on purpose).

Less likely to hold: `CODE_SIMILARITY_FLOOR = 0.08` and the top-K constants
in `coder/retrieval.py` are untuned guesses, not calibrated against a real
distribution of notes — I'd expect these to need adjustment once real
(non-sample) notes are run through it. The candidate/guideline retrieval
counts (6 codes, 8+4 guidelines) are similarly untuned.

## What I didn't build

- No calibration pass against real notes (I don't have any — see the
  brief's constraint on that).
- No sourced catalogue/guideline additions yet (above).
- Test coverage is a contract test and two retrieval tests, not a real
  suite against hard cases.
- No retry/backoff on the Anthropic client — a transient API error currently
  behaves the same as no key for that one note (falls through to
  `unresolved`), which is safe but not efficient at scale.

## Where this breaks at 50,000 codes instead of 404

The TF-IDF index is built in memory from two JSON files at process start;
that's fine at 404 entries and would still load at 50k, but per-candidate
LLM evaluation (one call per top-K code, in parallel) stops being the right
shape once "plausible candidates" for an ambiguous note routinely number in
the dozens rather than five. At that scale the retrieval step needs to do
more of the narrowing (a real ANN index, better than TF-IDF at
near-duplicate/hierarchical code families) so the LLM layer sees a materially
smaller, higher-precision candidate set — the five-agent split doesn't
change, but the K it's given would need to shrink relative to the catalogue
size, not stay fixed.

## Tooling

Built with Claude Code end to end. The one place it produced something
wrong that I caught: its first pass at `docker-compose.yml` used a fixed
`command:` for the note path, which silently violates the brief's "the
input path is an argument, not a constant" requirement — caught it and
reworked the run path into `run.sh`, which mounts an arbitrary host file at
run time instead of baking one into the compose file.
