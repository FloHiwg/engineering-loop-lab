"""One small GitHub-backed engineering loop."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loop_engineering_example.loop.storage import (
    Record,
    atomic_write_json,
    atomic_write_text,
    read_jsonl,
)
from loop_engineering_example.loop.triage import (
    CodexExplorer,
    ExplorerRuntime,
    build_triage_prompt,
    save_validated_result,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EVENTS_PATH = REPOSITORY_ROOT / "mock-systems" / "monitoring" / "events.jsonl"
RUNS_ROOT = REPOSITORY_ROOT / "runs"
WORKTREES_ROOT = REPOSITORY_ROOT / "worktrees"
LABEL = "loop-demo"
MACOS_CODEX_PATH = Path("/Applications/Codex.app/Contents/Resources/codex")


class WorkflowError(RuntimeError):
    """Raised when the demo cannot continue safely."""


class Runner(Protocol):
    def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> str: ...


class SubprocessRunner:
    def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> str:
        try:
            process = subprocess.run(
                command,
                cwd=cwd,
                input=input_text,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as error:
            raise WorkflowError(f"required command not found: {command[0]}") from error
        if check and process.returncode != 0:
            detail = process.stderr.strip() or process.stdout.strip()
            raise WorkflowError(f"{' '.join(command)} failed: {detail}")
        return process.stdout.strip()


@dataclass(frozen=True)
class RepositoryContext:
    name: str
    owner: str
    login: str
    default_branch: str


def codex_executable() -> str:
    configured = os.environ.get("CODEX_BIN")
    if configured:
        return configured
    discovered = shutil.which("codex")
    if discovered:
        return discovered
    if MACOS_CODEX_PATH.is_file():
        return str(MACOS_CODEX_PATH)
    raise WorkflowError(
        "Codex CLI was not found. Install it or set CODEX_BIN to its executable."
    )


class GitHub:
    def __init__(self, runner: Runner) -> None:
        self.runner = runner

    def context(self) -> RepositoryContext:
        try:
            self.runner.run(["gh", "auth", "status"])
        except WorkflowError as error:
            raise WorkflowError(
                "GitHub authentication is unavailable. Set GH_TOKEN to a "
                "fine-grained token limited to this fork with Issues and Pull "
                "requests read/write access."
            ) from error
        login = self.runner.run(["gh", "api", "user", "--jq", ".login"])
        raw = self.runner.run(
            [
                "gh",
                "repo",
                "view",
                "--json",
                "nameWithOwner,owner,defaultBranchRef",
            ]
        )
        data = json.loads(raw)
        context = RepositoryContext(
            name=data["nameWithOwner"],
            owner=data["owner"]["login"],
            login=login,
            default_branch=data["defaultBranchRef"]["name"],
        )
        if context.owner.casefold() != context.login.casefold():
            raise WorkflowError(
                f"origin resolves to {context.name}, which is not owned by "
                f"authenticated user {context.login}; fork it first"
            )
        return context

    def ensure_label(self, repository: str) -> None:
        self.runner.run(
            [
                "gh",
                "label",
                "create",
                LABEL,
                "--repo",
                repository,
                "--color",
                "1D76DB",
                "--description",
                "Created by the engineering loop demo",
                "--force",
            ]
        )

    def issues(self, repository: str, state: str = "all") -> list[Record]:
        raw = self.runner.run(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                repository,
                "--label",
                LABEL,
                "--state",
                state,
                "--limit",
                "100",
                "--json",
                "number,title,body,state,url",
            ]
        )
        return [
            issue
            for issue in json.loads(raw)
            if "<!-- loop-demo:" in (issue.get("body") or "")
        ]

    def create_issue(self, repository: str, event: Record) -> None:
        criteria = "\n".join(
            f"- {criterion}" for criterion in event["acceptance_criteria"]
        )
        body = (
            f"<!-- loop-demo:{event['event_id']} -->\n\n"
            f"Monitoring reported: {event['message']}\n\n"
            f"## Reproduction\n\n`{event['reproduce']}`\n\n"
            f"## Acceptance criteria\n\n{criteria}\n"
        )
        self.runner.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                repository,
                "--label",
                LABEL,
                "--title",
                event["title"],
                "--body",
                body,
            ]
        )

    def reopen_issue(self, repository: str, issue_number: int) -> None:
        self.runner.run(
            [
                "gh",
                "issue",
                "reopen",
                str(issue_number),
                "--repo",
                repository,
            ]
        )

    def pull_requests(self, repository: str, state: str = "all") -> list[Record]:
        raw = self.runner.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repository,
                "--state",
                state,
                "--limit",
                "100",
                "--json",
                "number,title,body,state,url,headRefName",
            ]
        )
        return [
            pull_request
            for pull_request in json.loads(raw)
            if re.fullmatch(
                r"loop-demo/issue-\d+",
                pull_request["headRefName"],
            )
            and "<!-- loop-demo -->" in (pull_request.get("body") or "")
        ]

    def create_pull_request(
        self,
        context: RepositoryContext,
        issue: Record,
        branch: str,
        report: Record,
    ) -> str:
        body = (
            "<!-- loop-demo -->\n\n"
            f"Closes #{issue['number']}\n\n"
            "Created by the engineering loop demo.\n\n"
            f"Success predicate: {report['success_predicate']}\n"
        )
        return self.runner.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                context.name,
                "--base",
                context.default_branch,
                "--head",
                branch,
                "--title",
                issue["title"],
                "--body",
                body,
            ]
        )


def load_events() -> list[Record]:
    events = read_jsonl(EVENTS_PATH)
    required = {
        "event_id",
        "title",
        "message",
        "reproduce",
        "acceptance_criteria",
    }
    for event in events:
        if not required.issubset(event):
            raise WorkflowError(f"incomplete monitoring event: {event}")
    return events


def event_id(issue: Record) -> str | None:
    marker = "<!-- loop-demo:"
    body = issue.get("body") or ""
    if marker not in body:
        return None
    return body.split(marker, 1)[1].split("-->", 1)[0].strip()


def setup_demo(github: GitHub) -> RepositoryContext:
    context = github.context()
    github.runner.run([codex_executable(), "--version"])
    github.ensure_label(context.name)
    existing = {event_id(issue): issue for issue in github.issues(context.name)}
    for event in load_events():
        issue = existing.get(event["event_id"])
        if issue is None:
            github.create_issue(context.name, event)
        elif issue["state"] != "OPEN":
            github.reopen_issue(context.name, issue["number"])
    print(f"Ready: {context.name}")
    print(f"Created or reused {len(load_events())} loop-demo issues.")
    return context


class Implementer:
    def __init__(self, runner: Runner, executable: str | None = None) -> None:
        self.runner = runner
        self.executable = executable or codex_executable()

    def run(self, worktree: Path, prompt: str, output_directory: Path) -> None:
        output_directory.mkdir(parents=True, exist_ok=True)
        atomic_write_text(output_directory / "prompt.txt", prompt)
        stderr_path = output_directory / "stderr.txt"
        command = [
            self.executable,
            "exec",
            "--sandbox",
            "workspace-write",
            "--ephemeral",
            "--ignore-user-config",
            "--color",
            "never",
            "-C",
            str(worktree),
            "-",
        ]
        process = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=worktree,
        )
        atomic_write_text(stderr_path, process.stderr)
        if process.returncode != 0:
            relative_path = stderr_path.relative_to(REPOSITORY_ROOT)
            raise WorkflowError(f"implementer failed; inspect {relative_path}")


class EngineeringLoop:
    def __init__(
        self,
        runner: Runner,
        github: GitHub,
        implementer: Implementer | None = None,
        explorer: ExplorerRuntime | None = None,
    ) -> None:
        self.runner = runner
        self.github = github
        self.implementer = implementer or Implementer(runner)
        self.explorer = explorer

    def next_issue(
        self,
        issues: list[Record],
        pull_requests: list[Record],
    ) -> Record | None:
        covered = {
            int(pull_request["headRefName"].rsplit("-", 1)[1])
            for pull_request in pull_requests
        }
        candidates = [
            issue
            for issue in issues
            if issue["state"] == "OPEN" and issue["number"] not in covered
        ]
        return min(candidates, key=lambda issue: issue["number"], default=None)

    def prepare_worktree(
        self,
        context: RepositoryContext,
        issue_number: int,
    ) -> tuple[str, Path]:
        branch = f"loop-demo/issue-{issue_number}"
        worktree = WORKTREES_ROOT / f"issue-{issue_number}"
        if worktree.exists():
            return branch, worktree
        self.runner.run(
            ["git", "fetch", "origin", context.default_branch],
            cwd=REPOSITORY_ROOT,
        )
        local_branch = self.runner.run(
            ["git", "branch", "--list", branch],
            cwd=REPOSITORY_ROOT,
            check=False,
        )
        command = ["git", "worktree", "add"]
        if local_branch:
            command.extend([str(worktree), branch])
        else:
            command.extend(
                [
                    "-b",
                    branch,
                    str(worktree),
                    f"origin/{context.default_branch}",
                ]
            )
        self.runner.run(command, cwd=REPOSITORY_ROOT)
        return branch, worktree

    def run_once(self) -> None:
        if self.runner.run(
            ["git", "status", "--porcelain"],
            cwd=REPOSITORY_ROOT,
        ):
            raise WorkflowError("main checkout must be clean before running the loop")
        context = self.github.context()
        issues = self.github.issues(context.name, state="open")
        pull_requests = self.github.pull_requests(context.name, state="open")
        issue = self.next_issue(issues, pull_requests)
        if issue is None:
            print("No unprocessed loop-demo issue remains.")
            return
        events = {event["event_id"]: event for event in load_events()}
        selected_event_id = event_id(issue)
        try:
            event = events[selected_event_id]
        except KeyError as error:
            raise WorkflowError("issue does not match a monitoring event") from error

        run_directory = RUNS_ROOT / f"issue-{issue['number']}"
        explorer = self.explorer or CodexExplorer(
            repository=REPOSITORY_ROOT,
            schema_path=REPOSITORY_ROOT / "agents" / "explorer.schema.json",
            executable=codex_executable(),
        )
        instructions = (REPOSITORY_ROOT / "agents" / "explorer.md").read_text()
        prompt = build_triage_prompt(instructions, event, issue, issue["body"])
        report = save_validated_result(
            run_directory / "triage",
            explorer.explore(prompt, run_directory / "triage"),
        )
        if report["decision"] != "ready":
            raise WorkflowError("triage escalated: " + "; ".join(report["ambiguities"]))

        branch, worktree = self.prepare_worktree(context, issue["number"])
        implementer_rules = (REPOSITORY_ROOT / "agents" / "implementer.md").read_text()
        implementation_prompt = (
            f"{implementer_rules}\n\n"
            f"## GitHub issue\n\n{issue['body']}\n\n"
            f"## Triage report\n\n```json\n"
            f"{json.dumps(report, indent=2, sort_keys=True)}\n```\n"
        )
        self.implementer.run(
            worktree,
            implementation_prompt,
            run_directory / "implementation",
        )
        self.runner.run(["make", "check"], cwd=worktree)
        if self.runner.run(["git", "status", "--porcelain"], cwd=worktree):
            self.runner.run(["git", "add", "-A"], cwd=worktree)
            self.runner.run(
                ["git", "commit", "-m", issue["title"]],
                cwd=worktree,
            )
        ahead = int(
            self.runner.run(
                [
                    "git",
                    "rev-list",
                    "--count",
                    f"origin/{context.default_branch}..HEAD",
                ],
                cwd=worktree,
            )
        )
        if ahead == 0:
            raise WorkflowError("implementer produced no commit")
        self.runner.run(["git", "push", "-u", "origin", branch], cwd=worktree)
        url = self.github.create_pull_request(context, issue, branch, report)
        atomic_write_json(
            run_directory / "result.json",
            {
                "issue": issue["number"],
                "branch": branch,
                "worktree": str(worktree.relative_to(REPOSITORY_ROOT)),
                "pull_request": url,
            },
        )
        print(f"Opened pull request: {url}")


def show_status(github: GitHub) -> None:
    context = github.context()
    issues = github.issues(context.name)
    pull_requests = github.pull_requests(context.name)
    print(f"Repository: {context.name}")
    print(f"Issues: {len(issues)} loop-demo issues")
    print(f"Pull requests: {len(pull_requests)} loop-demo pull requests")
    for issue in sorted(issues, key=lambda item: item["number"]):
        matching = next(
            (
                pull_request
                for pull_request in pull_requests
                if pull_request["headRefName"] == f"loop-demo/issue-{issue['number']}"
            ),
            None,
        )
        result = matching["url"] if matching else "waiting"
        print(f"- #{issue['number']} {issue['title']}: {result}")


def reset_demo(runner: Runner, github: GitHub, confirmed: bool) -> None:
    if not confirmed:
        raise WorkflowError("reset requires --yes because it closes remote demo items")
    context = github.context()
    for pull_request in github.pull_requests(context.name, state="open"):
        runner.run(
            [
                "gh",
                "pr",
                "close",
                str(pull_request["number"]),
                "--repo",
                context.name,
                "--delete-branch",
            ]
        )
    for issue in github.issues(context.name, state="open"):
        runner.run(
            [
                "gh",
                "issue",
                "close",
                str(issue["number"]),
                "--repo",
                context.name,
                "--reason",
                "not planned",
            ]
        )
    for worktree in WORKTREES_ROOT.glob("issue-*"):
        branch = f"loop-demo/{worktree.name}"
        runner.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=REPOSITORY_ROOT,
        )
        runner.run(
            ["git", "branch", "-D", branch],
            cwd=REPOSITORY_ROOT,
            check=False,
        )
    shutil.rmtree(RUNS_ROOT, ignore_errors=True)
    print("Closed loop-demo issues and pull requests and removed local run data.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "loop", "status", "reset"))
    parser.add_argument("--yes", action="store_true")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    runner = SubprocessRunner()
    github = GitHub(runner)
    actions = {
        "setup": lambda: setup_demo(github),
        "loop": lambda: EngineeringLoop(runner, github).run_once(),
        "status": lambda: show_status(github),
        "reset": lambda: reset_demo(runner, github, arguments.yes),
    }
    try:
        actions[arguments.command]()
    except WorkflowError as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
