# Loop Engineering Example

A deliberately small experiment showing how deterministic orchestration can
bound an AI agent working from monitoring evidence.

The current loop does five things:

```text
event -> ticket -> explorer -> validated decision -> state transition
```

It does not edit code yet. Complete requirements reach `READY`; incomplete
requirements reach `ESCALATED`.

## Try It

Requirements: Git, Python 3.12+, [uv](https://docs.astral.sh/uv/), and Make.

```bash
make setup
make check
make demo
```

`make demo` runs a real read-only Codex explorer against the division-by-zero
event. It requires local Codex authentication and network access.

The expected result is `READY`. Inspect the generated event, ticket, state, and
agent evidence with:

```bash
make inspect
```

Now run the same loop with an underspecified floating-point event:

```bash
make demo SCENARIO=ambiguous
make inspect SCENARIO=ambiguous
```

The expected result is `ESCALATED`. The explorer refuses to choose among exact
decimal arithmetic, rounding, formatting, or approximate comparison without a
defined product contract.

Generated data is stored under ignored `runs/<scenario>/` directories.

## What To Inspect

The five most useful files are:

| File | Purpose |
|---|---|
| `mock-systems/monitoring/events.jsonl` | Concrete input event |
| `scenarios/ambiguous-ticket/monitoring/events.jsonl` | Ambiguous input event |
| `agents/explorer.md` | Read-only role and judgment rules |
| `agents/explorer.schema.json` | Required structured output |
| `src/loop_engineering_example/loop/runner.py` | Deterministic state control |

After a demo, `runs/<scenario>/agent/triage/` contains the exact prompt, tool
transcript, raw result, and validated result. The agent proposes a decision;
ordinary Python validation decides whether the loop may advance.

## Application Under Test

`src/loop_engineering_example/app/` contains a tiny calculator API. Division by
zero intentionally escapes as a raw `ZeroDivisionError`:

```bash
make reproduce-division-by-zero
```

The defect remains unfixed at this checkpoint because the experiment currently
stops after triage.

## Repository Shape

```text
agents/                               # agent instructions and output schema
mock-systems/                         # readable file-backed external systems
scenarios/                            # alternate event inputs
src/loop_engineering_example/app/     # software being examined
src/loop_engineering_example/loop/    # orchestration, state, and adapters
tests/                                # deterministic behavior and boundaries
```

Each external system has its own adapter module. Shared JSON and atomic-write
helpers live in `loop/storage.py`.

## Replay Earlier Steps

Every completed phase has an immutable annotated Git tag:

```bash
git tag --list 'step-*'
git switch --detach step-04-agent-triage
```

Follow the README at that tag to replay its exact interface, then return with:

```bash
git switch main
```

The remaining roadmap and experiment questions are in [PLAN.md](PLAN.md).

## Limitations

- This is an educational experiment, not a production autonomous system.
- Agent behavior is non-deterministic even when orchestration is deterministic.
- File-backed systems model contracts and state, not real service operations.
- Measurements from one runtime, model, or task do not generalize by default.

## License

MIT
