# Repository Software Team Experiment

## 1. Purpose

Build a deliberately small, public, file-backed "software team in a
repository" to study agent loop design without hiding the important behavior
behind SaaS integrations.

The repository will demonstrate this loop:

```text
monitoring event
  -> create or associate ticket
  -> select actionable ticket
  -> explore the problem
  -> create isolated worktree
  -> implement change
  -> run CI
  -> independently verify
  -> open mock pull request
  -> update ticket and durable state
  -> stop, retry, or escalate
```

The project has three equally important outputs:

1. A working, dependency-light reference implementation.
2. A replayable public repository with checkpoints for each stage.
3. An evidence-based article about what worked, failed, and changed.

## 2. Guiding Principles

- Use agents for ambiguous reasoning and implementation.
- Use deterministic code for transitions, permissions, limits,
  deduplication, and evidence collection.
- Keep every external system human-readable and versionable.
- Make reruns idempotent: the same input must not create duplicate tickets,
  pull requests, or state transitions.
- Separate implementation from verification.
- Prefer explicit artifacts over conversational memory.
- Keep the first complete loop small before adding realism.
- Write conclusions from measured runs, not intended architecture.

## 3. Scope

### In scope

- Python 3.12 sample application.
- One intentional defect and one initially missing feature.
- File-backed monitoring, ticketing, CI, pull request, and memory adapters.
- Validated deterministic state machine.
- Explorer, implementer, and verifier roles.
- Git worktree isolation.
- Retry, cost, and escalation policies.
- Six controlled scenarios and several architecture comparisons.
- Reproducible commands, fixtures, logs, and documentation.

### Deferred

- Real databases, queues, Docker, and deployment infrastructure.
- Production security or multi-tenant operation.
- Real SaaS integrations until the file-backed loop is complete.
- Parallel work until the single-ticket lifecycle is stable.
- Optimization for token cost or throughput before measurements exist.

## 4. Target Repository Shape

```text
loop-engineering-example/
├── app/
│   ├── calculator.py
│   └── api.py
├── tests/
├── skills/
│   ├── triage/SKILL.md
│   ├── implement/SKILL.md
│   └── verify/SKILL.md
├── agents/
│   ├── explorer.md
│   ├── implementer.md
│   └── verifier.md
├── mock-systems/
│   ├── monitoring/events.jsonl
│   ├── tickets/index.json
│   ├── tickets/
│   ├── ci/runs.jsonl
│   └── pull-requests/
├── loop/
│   ├── adapters/
│   ├── prompts/
│   ├── run.py
│   ├── state.json
│   └── policy.yaml
├── scenarios/
│   ├── happy-path/
│   ├── failed-verification/
│   ├── ambiguous-ticket/
│   ├── duplicate-event/
│   ├── runaway-prevention/
│   └── parallel-work/
├── runs/
├── scripts/
│   ├── emit-monitoring-event.py
│   ├── run-ci.sh
│   ├── reset-demo.sh
│   └── replay.sh
├── AGENTS.md
├── LICENSE
├── Makefile
├── PLAN.md
└── README.md
```

An ignored local `docs/` tree holds article notes and interviews. Public
documentation should be added only when readers need it to understand or
replay the code.

## 5. Replay and Documentation Strategy

### Milestone checkpoints

Each implementation phase ends with:

- A green test suite.
- A numbered Git tag such as `step-01-sample-app`.
- A matching section in the README containing exact replay commands.
- A dated local experiment-log entry.
- A local article-note entry: expectation, observation, surprise, implication.
- A local checkpoint interview capturing the project owner's perspective.

Tags are immutable teaching checkpoints. The main branch contains the latest
complete version. A reader can use either:

```bash
git switch --detach step-03-deterministic-loop
make setup
make demo
```

or:

```bash
./scripts/replay.sh step-03-deterministic-loop happy-path
```

### Run artifacts

Every controlled execution receives a stable run ID and writes to
`runs/<run-id>/`:

```text
manifest.json
events.jsonl
state-transitions.jsonl
agent-turns.jsonl
ci-output.txt
diff.patch
verification.json
metrics.json
summary.md
```

Committed scenario fixtures remain deterministic. Generated local runs and
article evidence are ignored by default. Publish only evidence needed to
reproduce a concrete claim, and place it beside the relevant scenario.

### Experiment log entry

Every meaningful build step or run records:

- Date, commit, tag, scenario, and configuration.
- Question or hypothesis.
- Exact command and starting fixture.
- Expected result.
- Actual result and evidence paths.
- Metrics.
- Human interventions.
- Failure or unexpected behavior.
- Decision and next change.
- Candidate article takeaway.

Architecture decisions that matter to the article are recorded in ignored
local notes rather than added to the public repository as separate files.

## 6. Implementation Plan

### Phase 0: Establish the public experiment

Deliver:

- Initialize Git with `main` as the default branch.
- Add an MIT license and concise README suitable for a public educational
  repository.
- Add Python project metadata, pinned development dependencies, Makefile,
  formatting, linting, and tests.
- Add ignored local templates for experiment notes and checkpoint interviews.
- Record a local publishing checklist for secrets, personal data, and
  machine-specific paths.

Replay checkpoint: `step-00-project-skeleton`

Experiment question:

Can a fresh clone reproduce the development environment and understand the
experiment without private context?

Exit criteria:

- A fresh clone can run `make setup` and `make check`.
- README explains the purpose, limitations, and checkpoint model.

### Phase 1: Build the intentionally imperfect sample application

Deliver:

- Minimal calculator service and API boundary.
- Tests that describe existing supported behavior.
- A division-by-zero defect that is observable but not yet fixed.
- A missing feature with explicit acceptance criteria for a later scenario.
- Monitoring event fixtures derived from the defect.

Replay checkpoint: `step-01-sample-app`

Experiment question:

Can the failure be understood from the event, ticket, and repository without
hidden context?

Exit criteria:

- Baseline tests pass.
- A dedicated reproduction command reliably exposes the intentional defect.
- The defect is clearly documented so it is not mistaken for accidental bad
  code.

### Phase 2: Implement file-backed external systems

Deliver:

- Adapter interfaces for monitoring, ticketing, CI, pull requests, and state.
- JSON/JSONL/Markdown implementations behind those interfaces.
- Structured JSON return values for every adapter operation.
- Schemas and validation at all storage boundaries.
- Atomic writes where mutable files are required.
- Correlation IDs and deduplication keys.

Replay checkpoint: `step-02-file-backed-systems`

Experiment question:

Are file-backed systems readable enough for inspection while still enforcing
realistic contracts?

Exit criteria:

- Agents and orchestration never edit mock-system storage directly.
- Repeating the same event or command produces no duplicate side effects.
- Adapter contract tests cover success, invalid data, and repeated calls.

### Phase 3: Add the deterministic state machine

Deliver:

- States: `DISCOVERED`, `TRIAGED`, `READY`, `IMPLEMENTING`, `VERIFYING`,
  `PR_OPEN`, `DONE`, `BLOCKED`, `FAILED_RETRYABLE`, and `ESCALATED`.
- Explicit transition table and transition guards.
- Durable state containing ticket, branch, worktree, assigned role, attempt
  count, evidence, estimated cost, last error, and next action.
- CLI that advances exactly one transition or runs until a terminal state.
- Recovery after interruption.

Replay checkpoint: `step-03-deterministic-loop`

Experiment question:

Can the entire lifecycle run with scripted decisions before any agent is
introduced?

Exit criteria:

- All legal and illegal transitions are tested.
- Restarting at every state resumes without duplicating work.
- A scripted happy path reaches `DONE`.

### Phase 4: Add exploration and triage

Deliver:

- Explorer role with read-only permissions.
- Triage skill with an explicit input/output schema.
- Output containing relevant files, constraints, ambiguity, risk, and a
  testable success predicate.
- Escalation when required information or acceptance criteria are missing.
- Recorded prompts, tool calls, outputs, and estimated usage.

Replay checkpoint: `step-04-agent-triage`

Experiment question:

Does a bounded explorer improve task readiness, and can it detect ambiguity
without editing code?

Exit criteria:

- Happy-path ticket reaches `READY`.
- Ambiguous ticket reaches `ESCALATED`.
- Invalid or unstructured role output cannot advance state.

### Phase 5: Add isolated implementation

Deliver:

- One branch and Git worktree per actionable ticket.
- Implementer role restricted to its worktree.
- Implementation skill requiring the smallest viable change.
- Implementation report containing changed files, rationale, commands run,
  results, and unresolved concerns.
- Cleanup policy that preserves failed worktrees until evidence is collected.

Replay checkpoint: `step-05-isolated-implementation`

Experiment question:

What does worktree isolation prevent, and what integration work does it add?

Exit criteria:

- The intentional defect can be fixed in an isolated worktree.
- The main checkout remains unchanged during implementation.
- Interrupted implementation can resume from durable state.

### Phase 6: Add CI and independent verification

Deliver:

- CI adapter that runs formatting, linting, tests, and targeted reproduction.
- Append-only CI records with command, commit, status, duration, and output.
- Verifier role that receives the ticket, acceptance criteria, diff, and test
  evidence, but not the implementer's reasoning.
- Structured verdict: approve, reject with evidence, or escalate.
- Mock pull request created only after CI and verification succeed.

Replay checkpoint: `step-06-maker-checker`

Experiment question:

Does independent verification catch failures that self-review accepts?

Exit criteria:

- Happy path reaches `PR_OPEN` and then `DONE`.
- A deliberately incomplete fix is rejected.
- The verifier cannot modify the implementation.

### Phase 7: Add bounded retries and escalation

Deliver:

- Configurable retry, elapsed-time, turn, diff-size, and estimated-cost limits.
- Retry path that carries verifier evidence into the next attempt.
- Escalation report with history, evidence, last error, and recommended human
  action.
- Stop conditions enforced by the runner rather than role prompts.

Replay checkpoint: `step-07-bounded-loop`

Experiment question:

Do deterministic limits contain failure without discarding useful evidence?

Exit criteria:

- Failed verification retries exactly once under the default policy.
- Repeated failure stops at the configured boundary.
- No role can override a stop condition.

### Phase 8: Package the six scenarios

Deliver:

- Happy path.
- Failed verification followed by one retry.
- Ambiguous ticket escalation.
- Duplicate event correlation.
- Runaway prevention.
- Two independent tickets in parallel worktrees.
- Reset and replay commands for every scenario.
- One curated example run for each scenario.

Replay checkpoint: `step-08-scenario-suite`

Experiment question:

Can another person replay both successful and failed loop behavior from fixed
inputs without manually reconstructing state?

Exit criteria:

- `make scenarios` executes all deterministic portions.
- Each scenario documents expected states, side effects, and metrics.
- Repeated runs from reset fixtures produce equivalent outcomes.

### Phase 9: Run comparative experiments

Run repeated trials for:

| Comparison | Primary measures |
|---|---|
| Manual prompting vs loop | Human interventions, time, completion |
| Self-review vs verifier | False approvals, review time, retries |
| Shared checkout vs worktrees | Collisions, cleanup, integration time |
| Prompt-only vs skills | Repeated context, consistency, turns |
| Conversation vs state file | Recovery success after interruption |
| Unlimited vs bounded loop | Cost, attempts, failure containment |

Use at least five runs per non-deterministic configuration when practical.
Record runtime/model/version metadata because agent behavior can change.
Avoid claiming statistical significance; present this as an instrumented case
study with raw results.

Replay checkpoint: `step-09-experiment-results`

Experiment question:

Which loop design choices materially change reliability, human effort, cost,
and recovery behavior in this small system?

Exit criteria:

- Raw metrics and a reproducible analysis script are committed.
- Conclusions distinguish observations from interpretations.
- Failed and inconvenient runs remain represented.

### Phase 10: Replace one mock integration

Preferred candidate: GitHub Issues or GitHub Actions.

Deliver:

- A second adapter implementing the existing contract.
- Configuration switch between file-backed and real integration.
- Contract-test results for both implementations.
- Documentation of portability gaps and assumptions exposed by replacement.

Replay checkpoint: `step-10-real-adapter`

Experiment question:

Did the adapter boundary reflect the real service, or merely make the mock
look clean?

Exit criteria:

- The file-backed demo remains the default and works without credentials.
- Real integration is optional and safely documented.
- No secrets or account-specific data appear in committed artifacts.

### Phase 11: Publish the article

Build the article from the ignored local experiment and interview notes:

1. Why manual prompting stops scaling.
2. The smallest useful loop.
3. Why external systems were mocked as files.
4. Architecture and state machine.
5. One complete run.
6. Maker-checker separation.
7. Failures and incorrect assumptions.
8. Cost and orchestration overhead.
9. What worktrees solved and did not solve.
10. What remained deterministic.
11. When a loop is worth building.
12. Moving from file mocks to real integrations.

Replay checkpoint: `v1.0.0`

Experiment question:

Can every important article claim be reproduced or inspected directly in the
public repository?

Exit criteria:

- Every material claim links to code, a decision record, or run evidence.
- Commands and links are tested from a fresh clone.
- The repository and article state limitations and model/runtime versions.

## 7. Measurement Contract

Every run records:

- Completion status and terminal state.
- Number of role turns.
- Wall-clock duration.
- Approximate tokens and cost when available.
- Retry count.
- Tests and checks executed.
- Human interventions.
- Incorrect completion claims.
- Duplicate side effects.
- Review duration.
- Diff size.
- Commit, runtime, model, policy, and scenario versions.

Metrics are written by orchestration code, not self-reported by agents, except
where the runtime exposes no machine-readable usage data. Estimated values must
be labeled as estimates.

## 8. Verification Approach

- Unit tests: adapters, schemas, policies, transition guards, metrics.
- Contract tests: all adapter implementations.
- Integration tests: complete deterministic lifecycle using temporary files
  and temporary Git repositories.
- Scenario tests: fixture-to-terminal-state assertions.
- Fault injection: interruption, malformed role output, CI failure, duplicate
  events, stale worktrees, and partial writes.
- Manual replay: fresh clone on a second machine or clean environment before
  each tagged release.

## 9. Public Repository Safety

Before publishing or tagging:

- Scan tracked files and curated run artifacts for credentials and personal
  data.
- Remove absolute local paths and machine-specific environment values.
- Clearly label intentional vulnerabilities and defective checkpoints.
- Keep generated worktrees and uncurated run logs out of Git.
- Pin or record dependencies and agent runtime/model versions.
- Avoid requiring paid services for the core walkthrough.
- State that agent outputs are non-deterministic even when orchestration is
  deterministic.

## 10. Suggested First Working Slice

The first implementation slice should stop after Phase 3:

1. Create the imperfect calculator.
2. Emit a division-by-zero monitoring event.
3. Deterministically create and correlate a ticket.
4. Advance a scripted fix through CI, mock PR, and `DONE`.
5. Interrupt and rerun the loop at several states.
6. Publish the first four replay tags and document what was learned.

This establishes the contracts, state model, evidence format, and teaching
workflow before agent behavior adds variability.

## 11. Definition of Done

The project is complete when a new reader can:

1. Clone the public repository without credentials.
2. Replay each architectural milestone.
3. Run all six scenarios.
4. Inspect every external-system interaction as readable files.
5. Interrupt and resume a run without duplicate side effects.
6. Compare recorded configurations using committed raw evidence.
7. Trace article claims back to repository artifacts.
8. Replace an adapter without changing the state machine or role contracts.
