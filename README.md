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
tooling, and baseline test. It does not implement the software-team loop yet.

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
`make check` runs formatting checks, linting, and tests.

Useful commands:

```bash
make format
make test
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

## Experiment Notes

Draft article notes, decisions, and checkpoint interviews are maintained
locally under the ignored `docs/` directory. They are working material rather
than part of the public example.

## Limitations

- Agent behavior is non-deterministic even when orchestration is deterministic.
- File-backed systems model contracts and state, not the operational behavior
  of real services.
- Measurements from one runtime, model, or task do not generalize by default.
- The core walkthrough must remain usable without credentials or paid
  services.

## Contributing

Run `make check` and keep changes small, reproducible, and relevant to the
current checkpoint. Later checkpoints may intentionally contain defects; each
one will state what is expected.

## License

MIT
