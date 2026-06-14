# Loop Engineering Example

A deliberately small "software team in a repository" for studying agent loop
design. External systems are represented by readable files so the interesting
part remains visible: state, evidence, retries, isolation, review, and stopping
conditions.

This repository is an instrumented educational experiment, not a production
autonomous-development system. Some later checkpoints intentionally contain
defects or failed agent behavior. Each checkpoint documents what is expected.

## Current Checkpoint

`step-00-project-skeleton` establishes the public project, reproducible Python
tooling, documentation trail, and publication checks. It does not implement
the software-team loop yet.

The complete roadmap is in [PLAN.md](PLAN.md). [CLAUDE.md](CLAUDE.md) defines
the working rules used while building it.

## Requirements

- Git
- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)
- Make

## Setup

From a fresh clone:

```bash
make setup
make check
```

`make setup` creates a local virtual environment from the committed lockfile.
`make check` runs formatting checks, linting, tests, and the publication-safety
scanner.

Useful commands:

```bash
make format
make test
make publication-check
```

## Replaying Checkpoints

Each completed phase has an immutable annotated Git tag. To inspect this
checkpoint:

```bash
git switch --detach step-00-project-skeleton
make setup
make check
```

Return to current development with:

```bash
git switch main
```

Later checkpoints will add scenario-specific replay commands. Generated run
data belongs under `runs/` and is ignored unless deliberately curated for the
public evidence set.

## Evidence and Article Trail

- `docs/experiment-log.md` records expectations, commands, outcomes, and
  findings.
- `docs/decisions/` explains consequential architecture choices.
- `docs/example-runs/` will contain selected, publishable run evidence.

The project distinguishes direct observations from interpretations and does
not claim statistical significance from this small experiment.

Draft article notes and checkpoint interviews are maintained locally under
ignored `docs/` paths so unfinished editorial material and personal viewpoints
are not published with the full repository.

## Limitations

- Agent behavior is non-deterministic even when orchestration is deterministic.
- File-backed systems model contracts and state, not the operational behavior
  of real services.
- Measurements from one runtime, model, or task do not generalize by default.
- The core walkthrough must remain usable without credentials or paid
  services.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). By participating, you agree to follow
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Security

This repository may include intentionally defective code at clearly marked
teaching checkpoints. See [SECURITY.md](SECURITY.md) before reporting an issue.

## License

MIT
