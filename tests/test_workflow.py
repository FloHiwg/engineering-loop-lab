import json
import os
import subprocess
from pathlib import Path

import pytest

from loop_engineering_example.loop.workflow import (
    EngineeringLoop,
    GitHub,
    RepositoryContext,
    SubprocessRunner,
    WorkflowError,
    codex_executable,
    event_id,
    setup_demo,
)


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], str] | None = None) -> None:
        self.responses = responses or {}
        self.commands: list[tuple[str, ...]] = []

    def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> str:
        key = tuple(command)
        self.commands.append(key)
        return self.responses.get(key, "")


def repository_response(owner: str = "reader") -> str:
    return json.dumps(
        {
            "nameWithOwner": f"{owner}/engineering-loop-demo",
            "owner": {"login": owner},
            "defaultBranchRef": {"name": "main"},
        }
    )


def context_responses(owner: str = "reader", login: str = "reader") -> dict:
    return {
        ("gh", "api", "user", "--jq", ".login"): login,
        (
            "gh",
            "repo",
            "view",
            "--json",
            "nameWithOwner,owner,defaultBranchRef",
        ): repository_response(owner),
    }


def test_context_requires_repository_owned_by_authenticated_user() -> None:
    github = GitHub(FakeRunner(context_responses(owner="upstream", login="reader")))

    with pytest.raises(WorkflowError, match="fork it first"):
        github.context()


def test_context_explains_repository_scoped_authentication() -> None:
    class FailingRunner(FakeRunner):
        def run(
            self,
            command: list[str],
            *,
            cwd: Path | None = None,
            input_text: str | None = None,
            check: bool = True,
        ) -> str:
            raise WorkflowError("invalid token")

    with pytest.raises(WorkflowError, match="fine-grained token"):
        GitHub(FailingRunner()).context()


def test_codex_executable_prefers_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEX_BIN", "/custom/codex")

    assert codex_executable() == "/custom/codex"


def test_missing_command_has_friendly_error() -> None:
    missing = f"missing-command-{os.getpid()}"

    with pytest.raises(WorkflowError, match=f"required command not found: {missing}"):
        SubprocessRunner().run([missing])


def test_github_filters_unrelated_labeled_issues_and_prefixed_branches() -> None:
    responses = {
        (
            "gh",
            "issue",
            "list",
            "--repo",
            "reader/demo",
            "--label",
            "loop-demo",
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title,body,state,url",
        ): json.dumps(
            [
                {"number": 1, "body": "<!-- loop-demo:task-1 -->"},
                {"number": 2, "body": "unrelated"},
            ]
        ),
        (
            "gh",
            "pr",
            "list",
            "--repo",
            "reader/demo",
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title,body,state,url,headRefName",
        ): json.dumps(
            [
                {
                    "number": 1,
                    "body": "<!-- loop-demo -->",
                    "headRefName": "loop-demo/issue-1",
                },
                {
                    "number": 2,
                    "body": "",
                    "headRefName": "loop-demo/personal",
                },
            ]
        ),
    }
    github = GitHub(FakeRunner(responses))

    assert [issue["number"] for issue in github.issues("reader/demo")] == [1]
    assert [
        pull_request["number"] for pull_request in github.pull_requests("reader/demo")
    ] == [1]


def test_setup_creates_only_missing_monitoring_issues() -> None:
    responses = context_responses()
    responses[
        (
            "gh",
            "issue",
            "list",
            "--repo",
            "reader/engineering-loop-demo",
            "--label",
            "loop-demo",
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title,body,state,url",
        )
    ] = json.dumps(
        [
            {
                "number": 1,
                "title": "Handle division by zero",
                "body": "<!-- loop-demo:division-by-zero -->",
                "state": "OPEN",
                "url": "https://example.test/issues/1",
            }
        ]
    )
    runner = FakeRunner(responses)

    setup_demo(GitHub(runner))

    create_commands = [
        command
        for command in runner.commands
        if command[:3] == ("gh", "issue", "create")
    ]
    assert len(create_commands) == 2
    assert any("Add modulo support" in command for command in create_commands)
    assert any("Add power support" in command for command in create_commands)


def test_setup_reopens_closed_demo_issue() -> None:
    responses = context_responses()
    responses[
        (
            "gh",
            "issue",
            "list",
            "--repo",
            "reader/engineering-loop-demo",
            "--label",
            "loop-demo",
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title,body,state,url",
        )
    ] = json.dumps(
        [
            {
                "number": 7,
                "title": "Handle division by zero",
                "body": "<!-- loop-demo:division-by-zero -->",
                "state": "CLOSED",
                "url": "https://example.test/issues/7",
            }
        ]
    )
    runner = FakeRunner(responses)

    setup_demo(GitHub(runner))

    assert (
        "gh",
        "issue",
        "reopen",
        "7",
        "--repo",
        "reader/engineering-loop-demo",
    ) in runner.commands


def test_next_issue_skips_issues_that_already_have_pull_requests() -> None:
    loop = EngineeringLoop(FakeRunner(), GitHub(FakeRunner()))
    issues = [
        {"number": 4, "state": "OPEN"},
        {"number": 5, "state": "OPEN"},
    ]
    pull_requests = [{"headRefName": "loop-demo/issue-4"}]

    assert loop.next_issue(issues, pull_requests)["number"] == 5


def test_event_id_reads_marker() -> None:
    issue = {"body": "text\n<!-- loop-demo:modulo-operation -->\nmore"}

    assert event_id(issue) == "modulo-operation"


def test_prepare_worktree_resumes_existing_directory(tmp_path: Path) -> None:
    runner = FakeRunner()
    loop = EngineeringLoop(runner, GitHub(runner))
    context = RepositoryContext(
        name="reader/demo",
        owner="reader",
        login="reader",
        default_branch="main",
    )

    from loop_engineering_example.loop import workflow

    original = workflow.WORKTREES_ROOT
    workflow.WORKTREES_ROOT = tmp_path
    try:
        worktree = tmp_path / "issue-7"
        worktree.mkdir()
        branch, result = loop.prepare_worktree(context, 7)
    finally:
        workflow.WORKTREES_ROOT = original

    assert branch == "loop-demo/issue-7"
    assert result == worktree
    assert runner.commands == []


class FakeGitHub:
    def __init__(self, issues: list[dict[str, object]]) -> None:
        self._issues = issues
        self._pull_requests: list[dict[str, object]] = []

    def context(self) -> RepositoryContext:
        return RepositoryContext(
            name="reader/demo",
            owner="reader",
            login="reader",
            default_branch="main",
        )

    def issues(self, repository: str, state: str = "all") -> list[dict[str, object]]:
        return list(self._issues)

    def pull_requests(
        self,
        repository: str,
        state: str = "all",
    ) -> list[dict[str, object]]:
        return list(self._pull_requests)

    def create_pull_request(
        self,
        context: RepositoryContext,
        issue: dict[str, object],
        branch: str,
        report: dict[str, object],
    ) -> str:
        url = f"https://example.test/pull/{issue['number']}"
        self._pull_requests.append(
            {
                "number": issue["number"],
                "title": issue["title"],
                "body": "",
                "state": "OPEN",
                "url": url,
                "headRefName": branch,
            }
        )
        return url


class FakeExplorer:
    def explore(self, prompt: str, output_directory: Path) -> dict[str, object]:
        return {
            "decision": "ready",
            "summary": "The task is actionable.",
            "relevant_files": ["app.txt"],
            "constraints": [],
            "risks": [],
            "ambiguities": [],
            "success_predicate": "The task marker exists.",
            "recommended_tests": ["make check"],
            "confidence": 1.0,
        }


class FakeImplementer:
    def run(self, worktree: Path, prompt: str, output_directory: Path) -> None:
        issue_number = worktree.name.split("-", 1)[1]
        (worktree / f"task-{issue_number}.txt").write_text(
            "implemented\n",
            encoding="utf-8",
        )


def git(*arguments: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_three_loop_runs_create_three_branches_and_pull_requests(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = tmp_path / "repository"
    origin = tmp_path / "origin.git"
    repository.mkdir()
    git("init", "--bare", str(origin), cwd=tmp_path)
    git("init", "-b", "main", cwd=repository)
    git("config", "user.name", "Loop Demo", cwd=repository)
    git("config", "user.email", "loop@example.test", cwd=repository)
    (repository / ".gitignore").write_text("runs/\nworktrees/\n", encoding="utf-8")
    (repository / "Makefile").write_text("check:\n\t@true\n", encoding="utf-8")
    (repository / "app.txt").write_text("base\n", encoding="utf-8")
    (repository / "agents").mkdir()
    (repository / "agents" / "explorer.md").write_text(
        "Read only.\n",
        encoding="utf-8",
    )
    (repository / "agents" / "implementer.md").write_text(
        "Implement the task.\n",
        encoding="utf-8",
    )
    events = [
        {
            "event_id": f"task-{number}",
            "title": f"Task {number}",
            "message": "Test task",
            "reproduce": "true",
            "acceptance_criteria": ["Create the task marker."],
        }
        for number in (1, 2, 3)
    ]
    events_path = repository / "events.jsonl"
    events_path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )
    git("add", ".", cwd=repository)
    git("commit", "-m", "Initial", cwd=repository)
    git("remote", "add", "origin", str(origin), cwd=repository)
    git("push", "-u", "origin", "main", cwd=repository)

    issues = [
        {
            "number": number,
            "title": f"Task {number}",
            "body": f"<!-- loop-demo:task-{number} -->",
            "state": "OPEN",
            "url": f"https://example.test/issues/{number}",
        }
        for number in (1, 2, 3)
    ]

    from loop_engineering_example.loop import workflow

    original_values = (
        workflow.REPOSITORY_ROOT,
        workflow.EVENTS_PATH,
        workflow.RUNS_ROOT,
        workflow.WORKTREES_ROOT,
    )
    workflow.REPOSITORY_ROOT = repository
    workflow.EVENTS_PATH = events_path
    workflow.RUNS_ROOT = repository / "runs"
    workflow.WORKTREES_ROOT = repository / "worktrees"
    github = FakeGitHub(issues)
    try:
        loop = EngineeringLoop(
            SubprocessRunner(),
            github,  # type: ignore[arg-type]
            implementer=FakeImplementer(),  # type: ignore[arg-type]
            explorer=FakeExplorer(),
        )
        loop.run_once()
        loop.run_once()
        loop.run_once()
    finally:
        (
            workflow.REPOSITORY_ROOT,
            workflow.EVENTS_PATH,
            workflow.RUNS_ROOT,
            workflow.WORKTREES_ROOT,
        ) = original_values

    assert len(github._pull_requests) == 3
    branches = git("branch", "--remotes", cwd=repository)
    assert "origin/loop-demo/issue-1" in branches
    assert "origin/loop-demo/issue-2" in branches
    assert "origin/loop-demo/issue-3" in branches
    output = capsys.readouterr().out
    assert "Starting one engineering-loop run." in output
    assert "Running the read-only triage agent." in output
    assert "Running the implementation agent." in output
    assert "All checks passed." in output
    assert "Opened pull request:" in output
