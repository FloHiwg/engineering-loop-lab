# Plan

Build one deliberately small, forkable engineering loop that a reader can run
without understanding agent orchestration first.

## Reader Outcome

After `make setup` and three `make loop` calls, the reader sees:

- Three GitHub Issues created from mocked monitoring events.
- Three isolated worktrees and implementation branches.
- Three tested commits.
- Three open pull requests in their fork.
- Local prompts, transcripts, triage evidence, and run results.

## Public Commands

```text
make setup   install dependencies and seed GitHub Issues
make loop    process one issue and open one pull request
make status  show issues and pull requests
make reset   close demo resources and remove local run data
make check   run repository checks
```

## Safety

- Refuse setup unless `origin` belongs to the authenticated GitHub user.
- Support a fine-grained `GH_TOKEN` restricted to the reader's fork.
- Mark every remote resource with `loop-demo`.
- Never merge pull requests.
- Restrict implementation to a dedicated worktree.
- Require explicit confirmation before reset closes remote resources.
- Keep prompts, run data, and worktrees out of Git.
- Keep one `pre-github-loop-demo` tag as the pre-redesign restore point.

## Article Evidence

Record:

- What the reader runs and sees.
- How the loop chooses work.
- What remains deterministic.
- What worktree isolation prevents.
- Failures, retries, duration, and token usage.
- Where the demo stops being representative of a production system.

The article should explain one complete run, then show that restarting the same
loop processes the next issue without rebuilding the orchestration.
