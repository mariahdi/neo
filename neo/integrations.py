"""Integration clients.

These are the seams where Neo touches the outside world. They are stubbed
with real method signatures and TODOs rather than fake implementations, so
the interface is clear and a dry run can narrate the flow without doing
anything destructive.

Real implementations:
  - Jira:   Atlassian REST API v3 (issue create / transition).
  - GitHub: REST API or `gh` CLI (branch, commit, pull request).
  - Claude: Anthropic Messages API (draft generation with a loaded skill).
"""
from __future__ import annotations

from typing import Protocol


class Reporter(Protocol):
    def say(self, msg: str) -> None: ...


class ConsoleReporter:
    """Prints what *would* happen. Used in --dry-run."""
    def say(self, msg: str) -> None:
        print(f"   · {msg}")


class JiraClient:
    def __init__(self, base_url: str = "", reporter: Reporter | None = None):
        self.base_url = base_url
        self.reporter = reporter or ConsoleReporter()

    def transition(self, key: str, to_state: str) -> None:
        self.reporter.say(f"Jira: move {key} -> {to_state}")
        # TODO: POST /rest/api/3/issue/{key}/transitions

    def comment(self, key: str, body: str) -> None:
        self.reporter.say(f"Jira: comment on {key}: {body[:60]}...")
        # TODO: POST /rest/api/3/issue/{key}/comment


class GitHubClient:
    def __init__(self, repo: str = "", reporter: Reporter | None = None):
        self.repo = repo
        self.reporter = reporter or ConsoleReporter()

    def checkout_branch(self, branch: str) -> None:
        self.reporter.say(f"GitHub: checkout {branch}")
        # TODO: create/checkout feature branch

    def commit_file(self, branch: str, path: str, content: str) -> None:
        self.reporter.say(f"GitHub: commit {path} on {branch} ({len(content)} chars)")
        # TODO: commit the draft so reviewers can comment inline

    def open_pull_request(self, branch: str, title: str) -> str:
        self.reporter.say(f"GitHub: open PR for {branch} — '{title}'")
        # TODO: open PR, return its URL
        return f"https://github.com/{self.repo or 'owner/neo'}/pull/NEW"


class ClaudeClient:
    """Claude acts as one of the developers: it drafts the work."""
    def __init__(self, reporter: Reporter | None = None):
        self.reporter = reporter or ConsoleReporter()

    def draft(self, request: str, skill_text: str) -> str:
        self.reporter.say("Claude: drafting with the loaded skill")
        # TODO: call the Anthropic Messages API with `skill_text` as system
        # context and `request` as the task. Return the generated draft.
        return (
            "# DRAFT (placeholder)\n\n"
            f"Request: {request}\n\n"
            "This is where Claude's drafted proposal will appear once the "
            "Anthropic API is wired in. The loaded skill shaped this output."
        )
