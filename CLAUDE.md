# Working Agreement

`PLAN.md` is the source of truth for scope and the reader journey. This file
only defines how work is conducted.

## Rules

- Keep changes and commits focused, reviewable, and replayable.
- Do not hide failed attempts, surprises, or negative results.
- Run all applicable checks and never claim completion when checks were
  skipped or failed.
- Keep secrets, personal data, absolute local paths, and machine-specific
  values out of committed artifacts.

## Workflow

For every meaningful change:

1. Record the question and expected outcome in the ignored local article notes.
2. Implement and verify it in focused commits.
3. Record commands, evidence, metrics, failures, surprises, decisions,
   learnings, and possible article claims in those local notes.
4. Interview the user when their experience or judgment matters to the article.
5. Keep private article material under ignored `docs/`.

## Completion Gate

A change is complete only when:

- Relevant checks pass.
- The reader workflow works from a clean fork or a faithful local test double.
- Private article notes are updated.
