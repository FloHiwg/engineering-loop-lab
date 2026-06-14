# 0001: Use uv for Python tooling

- Status: Accepted
- Date: 2026-06-14

## Context

The public repository needs a short setup path, a reproducible dependency lock,
and isolated command execution without adding containers or a custom bootstrap
script.

## Decision

Use Python 3.12+ with `uv`. Commit `uv.lock`, use `uv sync --locked` for setup,
and execute project tools through `uv run`. Make targets set `UV_CACHE_DIR` to
an ignored repository-local directory so execution does not depend on access
to a global user cache.

## Alternatives

- Standard-library `venv` plus pip requirements files.
- Poetry, PDM, or Hatch environment management.
- Docker.

## Consequences

Readers need one additional tool, but setup and command execution remain
concise and dependency versions are locked. Docker remains unnecessary.

## Revisit When

Fresh-clone testing shows that installing or using `uv` is a meaningful barrier
for readers, or the project needs packaging behavior that this setup cannot
express clearly.
