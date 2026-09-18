---
name: commit-discipline
description: "Commit cadence and message style for this project — small commits as the build progresses, human-written short messages, no squashing, no AI attribution footer."
---

# Commit discipline for this project

Used for every commit made while building the clinical coding system.

## Cadence

- Commit as each working slice lands: data loading, retrieval, reasoning
  step, output contract, CLI, Docker, README, each data addition, each
  fix. Small, working, reviewable steps — not one commit at the end.
- Include commits for things that got backed out or reworked. The brief
  reads the history as the only evidence of how the work happened; a
  history that hides dead ends is graded down same as a squash.
- Never rewrite or force-push history to hide a mistake or a revert — a
  visible revert commit is more honest than a rebase that erases it.

## Message style

- Short, plain, human-sounding. Present tense, no ceremony
  ("add TF-IDF retrieval over catalog synonyms", not "Implemented feature
  for retrieval mechanism").
- One line is usually enough; add a body only if the "why" isn't obvious
  from the diff.
- No AI attribution footer/trailer on commits in this repo — this overrides
  the default Claude Code attribution behavior for this project specifically.
- No emoji, no marketing tone, no "this commit adds comprehensive support
  for...".

## Before committing

- Confirm no API keys or secrets are staged (the pipeline reads keys from
  the environment only — see [[coding-output-contract]]).
- Confirm `data/icd_catalog.json` and `data/guideline_snippets.json`
  (the supplied files) are unmodified — additions go in the separate files
  described in [[data-expansion]].
