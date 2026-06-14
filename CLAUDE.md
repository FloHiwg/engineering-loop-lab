# Working Agreement

`PLAN.md` is the source of truth for scope, phases, checkpoint names, and exit
criteria. This file only defines how work is conducted.

## Rules

- Work one checkpoint at a time and do not silently move to the next.
- Keep changes and commits focused, reviewable, and replayable.
- Do not hide failed attempts, surprises, or negative results.
- Run all applicable checks and never claim completion when checks were
  skipped or failed.
- Never tag a checkpoint before its implementation, tests, replay
  instructions, and documentation are complete.
- Treat published checkpoint tags as immutable.
- Keep secrets, personal data, absolute local paths, and machine-specific
  values out of committed artifacts.

## Checkpoint Workflow

For every checkpoint:

1. Record its question, assumptions, expected outcome, and exit criteria in
   `docs/experiment-log.md`.
2. Implement and verify it in focused commits.
3. Record commands, evidence, metrics, failures, surprises, decisions,
   learnings, and possible article claims.
4. Summarize expectation, observation, surprise, and implication in
   `docs/article-notes.md`.
5. Interview the user with three to five questions about their reaction,
   experience, disagreements, and what matters for the article. Record their
   answers in `docs/interviews/<checkpoint>.md` and do not invent their view.
6. Add a dedicated checkpoint commit and the exact annotated tag from
   `PLAN.md`.
7. Report the commit, tag, checks, replay command, findings, and open questions.
8. Wait for user review before starting the next checkpoint unless continuous
   execution was explicitly requested.

## Completion Gate

A checkpoint is complete only when:

- Its exit criteria and relevant checks pass.
- Replay instructions work from a clean checkout.
- Findings and article notes are updated.
- The user interview is recorded or explicitly marked pending.
- The checkpoint commit and annotated tag exist.
