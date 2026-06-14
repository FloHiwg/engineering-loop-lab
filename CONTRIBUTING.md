# Contributing

Contributions that make the experiment clearer, smaller, more reproducible, or
better evidenced are welcome.

## Before Opening a Change

1. Read `README.md`, `PLAN.md`, and `CLAUDE.md`.
2. Keep the change within the current checkpoint or explain why the plan should
   change.
3. Add or update tests for behavior changes.
4. Run `make check`.
5. Document findings rather than presenting assumptions as results.

Keep commits focused. Do not include generated run data unless it is selected,
reviewed evidence for `docs/example-runs/`.

## Reporting Problems

Include the checkpoint tag, operating system, Python and `uv` versions, exact
command, expected result, actual result, and any non-sensitive output needed to
reproduce the problem.
