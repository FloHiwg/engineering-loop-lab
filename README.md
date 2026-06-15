# Engineering Loop Demo

Fork this repository and watch a small AI software team create three pull
requests in your fork.

```text
monitoring event + GitHub issue
              |
              v
           triage
              |
              v
     isolated Git worktree
              |
              v
      implement and test
              |
              v
       open pull request
```

Each loop run processes exactly one issue and stops after opening its pull
request. It never merges automatically.

## Requirements

- Git
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [GitHub CLI](https://cli.github.com/)
- [Codex CLI](https://developers.openai.com/codex/cli/) authenticated locally

On macOS, setup automatically detects the CLI bundled with `Codex.app`. For a
custom installation, set `CODEX_BIN` to the executable path.

Your `origin` remote must point to a fork owned by the authenticated GitHub
user. Setup refuses to create anything in another user's repository.

### Repository-Scoped GitHub Access

Use a short-lived
[fine-grained personal access token](https://github.com/settings/personal-access-tokens/new)
instead of granting GitHub CLI broad account access:

1. Select your account as the resource owner.
2. Select only this fork under repository access.
3. Grant repository permissions:
   - Contents: Read
   - Issues: Read and write
   - Pull requests: Read and write
4. Choose a short expiration.

Load it into the current terminal without echoing it:

```bash
read -s GH_TOKEN
export GH_TOKEN
```

Paste the token, press Enter, and keep that terminal open while running the
demo. Git pushes use your existing SSH key. Remove the token afterward with
`unset GH_TOKEN`.

## Run It

```bash
make setup
make loop
make loop
make loop
make status
```

`make setup` installs dependencies and idempotently creates three GitHub Issues
from `mock-systems/monitoring/events.jsonl`.

Each `make loop`:

1. Reads the open demo issues and monitoring events.
2. Picks the oldest issue without a pull request.
3. Uses a read-only explorer to establish a testable success predicate.
4. Creates or resumes `worktrees/issue-<number>`.
5. Lets an implementer make the smallest viable change there.
6. Runs `make check`, commits, pushes, and opens a pull request.

After three runs, your fork has three open pull requests. Keeping the runs
separate makes it easy to inspect how the same loop picks the next issue each
time.

Generated prompts, transcripts, and results live under ignored `runs/`.
Worktrees live under ignored `worktrees/`.

## Start Again

```bash
make reset
```

Reset is intentionally guarded because it closes remote demo issues and pull
requests. First inspect what will be affected with `make status`, then run:

```bash
make reset CONFIRM=1
```

It only touches issues labeled `loop-demo`, branches named `loop-demo/*`, and
matching local worktrees.

Then run `make setup` again.

To inspect the repository as it existed before the GitHub-backed redesign:

```bash
git switch --detach pre-github-loop-demo
```

Return to the current version with `git switch main`.

## What Is Mocked?

Only monitoring is mocked as three readable JSON lines. GitHub Issues, Git
branches, worktrees, commits, and pull requests are real and belong to your
fork.

The sample application is a deliberately incomplete calculator under
`src/loop_engineering_example/app/`.

## Limits

- This is an educational demo, not a production autonomous system.
- Agent output is non-deterministic.
- Pull requests may overlap because they all start from the fork's default
  branch and remain open for inspection.
- Setup and reset perform real writes in your fork.

## License

MIT
