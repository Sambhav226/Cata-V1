---
name: agent-architecture
description: "The multi-agent pipeline shape for the clinical coding system — five narrow agents plus a deterministic fallback. Use when adding/changing any agent, the orchestrator, or the LLM client wrapper."
---

# Agent architecture

Used when touching `coder/agents/*`, `coder/pipeline.py`, or `coder/llm.py`.

## The shape

```
note -> Extractor -> Retrieval (stdlib TF-IDF) -> [Candidate agent per code, parallel]
                                                 -> Conflict Auditor (parallel with candidates)
                                                 -> Adjudicator -> CodingRecord
```

Five roles, each independently testable and each mapped to a specific brief
requirement — not a chain of generic "LLM step" functions.

## Roles and their one job

1. **Extractor** (`agents/extractor.py`) — turns raw note text into a
   structured clinical picture (complaint, findings, duration, stated
   diagnosis if any, notable absences). It never proposes a code. This is
   what stops downstream steps from pattern-matching on note phrasing —
   the extractor's output is phrasing-independent by construction.
2. **Candidate agent** (`agents/candidate.py`) — evaluates exactly one
   candidate code against the note + picture + that code's targeted
   guideline retrieval. Must return both supporting and disqualifying
   reasoning for that single code, with citations. Runs once per top
   candidate, in parallel (`concurrent.futures`), never sees the other
   candidates — this is what prevents anchoring on the first plausible code.
3. **Conflict Auditor** (`agents/auditor.py`) — reads every retrieved
   guideline across all candidates together, looking for guideline-vs-
   guideline contradiction and unannounced restrictions (see
   [[guideline-conflicts]]). Runs in parallel with the candidate agents,
   not folded into any one of them.
4. **Adjudicator** (`agents/adjudicator.py`) — the only agent allowed to
   write the final `CodingRecord`. Takes the picture + all candidate
   verdicts + the auditor's findings and decides code(s)/refusal/
   confidence/unresolved (see [[coding-output-contract]]). Must cite
   sub-agent findings, not re-derive evidence itself — if the adjudicator's
   reasoning references something no sub-agent surfaced, that's a bug.
5. **Deterministic fallback** (`agents/fallback.py`) — used per-agent-slot
   whenever no LLM key/client is available. Not a second reasoning engine:
   a similarity-margin threshold that leans toward `unresolved`. The brief
   expects the no-key path to be thin — don't over-build it.

## Orchestrator rules (`pipeline.py`)

- One `try/except` per note. A failure anywhere in the chain produces an
  `unresolved` record for that note and the batch continues — see
  [[coding-output-contract]].
- Candidate agents and the auditor run concurrently (`ThreadPoolExecutor`),
  not sequentially — they don't depend on each other's output.
- The adjudicator runs last and is the only step with a hard sequential
  dependency on everything else.
- `coder/llm.py` is the single choke point for "is a model available."
  Every agent asks it for a completion; agents never check
  `os.environ` themselves. If the client returns `None` (no key, import
  failure, or a call error), the agent falls through to its fallback slot.

## Anti-patterns to reject in review

- One big prompt holding the note, all candidates, and all guidelines,
  asked to "pick the best code and check for issues" in one shot — this is
  the anchoring failure mode the split architecture exists to avoid.
- An agent reading `os.environ["ANTHROPIC_API_KEY"]` directly instead of
  going through `coder/llm.py`.
- The fallback path trying to replicate LLM-quality reasoning
  deterministically — it should refuse more, not less, than the LLM path.
