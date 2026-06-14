# Experiment Log

This is the chronological record of planned checkpoints and observed runs.
Keep expectations visible when later evidence contradicts them.

## 2026-06-14: `step-00-project-skeleton`

### Question

Can a fresh clone reproduce the development environment and understand the
experiment without private context?

### Assumptions

- Git, Make, Python 3.12+, and `uv` are acceptable bootstrap requirements.
- A committed `uv.lock` is sufficient to reproduce development dependencies.
- A small baseline package and test prove the toolchain without implementing
  Phase 1 early.
- Public documentation should make the project's intentional defects and
  non-production status explicit.

### Expected Outcome

A fresh checkout can run `make setup` and `make check`, and a reader can
understand the purpose, limitations, checkpoint model, and evidence trail from
the README.

### Exit Criteria

- [x] A fresh clone can run `make setup` and `make check`.
- [x] README explains the purpose, limitations, and checkpoint model.

### Implementation Record

- Checkpoint commit: this checkpoint commit
- Runtime: CPython 3.13.12
- Dependency manager: `uv`
- Locked tools: pytest 8.4.2 and Ruff 0.15.17

Commands run:

```text
uv lock
make setup
make format
make check
rsync publishable files into a new temporary directory
git init -b main
make setup
make check
```

Clean-checkout verification used a new temporary Git repository without the
source repository's `.git`, `.venv`, or `.uv-cache` directories. Setup
downloaded only packages named in `uv.lock`.

Verification result:

- Ruff formatting: passed, 5 Python files checked.
- Ruff linting: passed.
- pytest: passed, 4 tests.
- Publication scanner: passed.
- Clean-checkout setup and full check: passed.

Human interventions:

- Network access was approved for dependency locking and clean installation.
- No implementation decisions required manual code repair outside the normal
  build-and-test loop.

### Findings

**Observation:** The first `uv lock` attempt failed because its default cache
was outside the restricted workspace. Setting `UV_CACHE_DIR` to an ignored
repository-local directory removed that dependency on ambient user state.

**Observation:** The first lint run caught an unused import. The first test run
then exposed that repository-root scripts are not reliable import targets for
an installed package. Moving scanner logic into the package fixed the boundary.

**Observation:** The publication scanner initially detected the path patterns
in its own source and test fixtures. A line-level `publication-check: allow`
marker made exemptions explicit and reviewable.

**Observation:** After those corrections, the documented two-command setup
worked in a clean temporary repository.

**Interpretation:** Even a minimal project skeleton benefits from testing in a
clean repository. Local success alone would have hidden the cache and import
boundary assumptions.

**Open question:** Is the current amount of repository ceremony proportionate
to the educational value, or should later checkpoints consolidate some files?

The project owner reported no major surprise in the initial setup. They asked
that article notes remain ignored rather than being published with the
repository; checkpoint interview material is kept private alongside those
notes.
