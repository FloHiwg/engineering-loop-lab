# Loop Engineering Example

A deliberately small "software team in a repository" for studying agent loop
design. External systems are represented by readable files so the interesting
part remains visible: state, evidence, retries, isolation, review, and stopping
conditions.

This repository is an instrumented educational experiment, not a production
autonomous-development system. Some later checkpoints intentionally contain
defects or failed agent behavior. Each checkpoint documents what is expected.

## Current Checkpoint

`step-01-sample-app` adds the intentionally imperfect calculator used by later
loop scenarios. The software-team loop itself is not implemented yet.

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
make reproduce-division-by-zero
```

## Sample Application

The application has a pure calculator service and a small dictionary-based API
boundary. It supports `add`, `subtract`, `multiply`, and `divide`.

### Intentional Defect

Division by zero is deliberately unhandled and escapes the API boundary as a
raw `ZeroDivisionError`. This is the monitoring-driven defect that a later
checkpoint will ask the loop to fix.

Reproduce and verify it with:

```bash
make reproduce-division-by-zero
```

The matching readable monitoring event is in
`mock-systems/monitoring/events.jsonl`. Baseline tests intentionally cover only
supported behavior; the reproduction command guards the defective checkpoint.

### Missing Feature

The `modulo` operation is intentionally absent. Its acceptance criteria are:

- A request with `operation: "modulo"` returns the remainder of `left / right`.
- Numeric validation matches the existing operations.
- A zero right operand returns a controlled application error rather than a
  raw Python exception.
- Existing operations keep their current behavior.

## Replaying Checkpoints

Each completed phase has an immutable annotated Git tag. To inspect this
checkpoint:

```bash
git switch --detach step-01-sample-app
make setup
make check
make reproduce-division-by-zero
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
