"""Integration clients.

These are the seams where Neo touches the outside world.

Each integration has two variants that share one interface:
  - a Dry* client that only narrates ("what would happen"), used by --dry-run
  - a Live* client that actually calls the API

GitHub and Jira are now live; Claude is still a dry-only stub. The loop is
agnostic — it just calls the methods on whatever client it's given.

Jira uses the Atlassian Cloud REST API v3 over stdlib urllib (no extra
deps). Credentials come from the environment, never the repo:
    NEO_JIRA_BASE_URL   e.g. https://mariahdiharris.atlassian.net
    NEO_JIRA_EMAIL      your Atlassian account email
    NEO_JIRA_API_TOKEN  from id.atlassian.com/manage-profile/security/api-tokens
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Optional, Protocol


class Reporter(Protocol):
    def say(self, msg: str) -> None: ...


class ConsoleReporter:
    def say(self, msg: str) -> None:
        print(f"   . {msg}")


# --------------------------------------------------------------------------
# Jira
# --------------------------------------------------------------------------
def _adf(text: str) -> dict:
    """Minimal Atlassian Document Format wrapper (API v3 needs this)."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph",
                     "content": [{"type": "text", "text": text}]}],
    }


class DryJiraClient:
    def __init__(self, base_url: str = "", reporter: Reporter | None = None):
        self.base_url = base_url
        self.reporter = reporter or ConsoleReporter()

    def create_issue(self, project: str, summary: str, issue_type: str = "Task",
                     description: str = "") -> str:
        self.reporter.say(f"Jira: create {issue_type} in {project} — '{summary}'")
        return f"{project}-NEW"

    def transition(self, key: str, to_state: str) -> None:
        self.reporter.say(f"Jira: move {key} -> {to_state}")

    def comment(self, key: str, body: str) -> None:
        self.reporter.say(f"Jira: comment on {key}: {body[:60]}...")


class LiveJiraClient:
    """Real Jira Cloud client. Reads creds from the environment."""

    def __init__(self, base_url: str = "", reporter: Reporter | None = None):
        self.base_url = (base_url or os.environ.get("NEO_JIRA_BASE_URL", "")).rstrip("/")
        self.reporter = reporter or ConsoleReporter()
        email = os.environ.get("NEO_JIRA_EMAIL", "")
        token = os.environ.get("NEO_JIRA_API_TOKEN", "")
        if not (self.base_url and email and token):
            raise RuntimeError(
                "Live Jira needs NEO_JIRA_BASE_URL, NEO_JIRA_EMAIL and "
                "NEO_JIRA_API_TOKEN in the environment."
            )
        self._auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/rest/api/3{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Basic {self._auth}")
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            raise RuntimeError(f"Jira {method} {path} -> {e.code}: {detail}") from None

    def create_issue(self, project: str, summary: str, issue_type: str = "Task",
                     description: str = "") -> str:
        fields = {"project": {"key": project},
                  "summary": summary,
                  "issuetype": {"name": issue_type}}
        if description:
            fields["description"] = _adf(description)
        res = self._request("POST", "/issue", {"fields": fields})
        key = res.get("key", "?")
        self.reporter.say(f"Jira: created {key} — '{summary}'")
        return key

    def _transition_id(self, key: str, to_state: str) -> Optional[str]:
        res = self._request("GET", f"/issue/{key}/transitions")
        for t in res.get("transitions", []):
            if t.get("to", {}).get("name", "").lower() == to_state.lower():
                return t["id"]
        return None

    def transition(self, key: str, to_state: str) -> None:
        # Jira status names are Title Case ("In Progress", "In Review").
        target = to_state.replace("_", " ").title()
        tid = self._transition_id(key, target)
        if tid is None:
            self.reporter.say(
                f"Jira: no transition to '{target}' for {key} "
                f"(is the column added to the board?) — skipped"
            )
            return
        self._request("POST", f"/issue/{key}/transitions", {"transition": {"id": tid}})
        self.reporter.say(f"Jira: moved {key} -> {target}")

    def comment(self, key: str, body: str) -> None:
        self._request("POST", f"/issue/{key}/comment", {"body": _adf(body)})
        self.reporter.say(f"Jira: commented on {key}")


# --------------------------------------------------------------------------
# GitHub
# --------------------------------------------------------------------------
class _ApiError(RuntimeError):
    def __init__(self, code: int, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class DryGitHubClient:
    def __init__(self, repo: str = "", reporter: Reporter | None = None):
        self.repo = repo
        self.reporter = reporter or ConsoleReporter()

    def checkout_branch(self, branch: str) -> None:
        self.reporter.say(f"GitHub: checkout {branch}")

    def commit_file(self, branch: str, path: str, content: str) -> None:
        self.reporter.say(f"GitHub: commit {path} on {branch} ({len(content)} chars)")

    def open_pull_request(self, branch: str, title: str) -> str:
        self.reporter.say(f"GitHub: open PR for {branch} — '{title}'")
        return f"https://github.com/{self.repo or 'owner/neo'}/pull/NEW"


class LiveGitHubClient:
    """Real GitHub client over the REST API (stdlib urllib).

    Env:
        NEO_GITHUB_REPO   owner/repo, e.g. mariahdi/neo
        NEO_GITHUB_TOKEN  a fine-grained PAT with Contents + Pull requests
                          read/write on the repo
    """
    API = "https://api.github.com"

    def __init__(self, repo: str = "", reporter: Reporter | None = None):
        self.repo = repo or os.environ.get("NEO_GITHUB_REPO", "")
        self.reporter = reporter or ConsoleReporter()
        token = os.environ.get("NEO_GITHUB_TOKEN", "")
        if not (self.repo and token):
            raise RuntimeError(
                "Live GitHub needs NEO_GITHUB_REPO (owner/repo) and "
                "NEO_GITHUB_TOKEN in the environment."
            )
        self._token = token
        self._default_branch: Optional[str] = None
        self._base_sha: Optional[str] = None

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        url = f"{self.API}{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "neo-loop")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise _ApiError(e.code, e.read().decode()[:300]) from None

    def _ensure_base(self) -> None:
        if self._base_sha is not None:
            return
        repo = self._request("GET", f"/repos/{self.repo}")
        self._default_branch = repo.get("default_branch", "main")
        ref = self._request("GET", f"/repos/{self.repo}/git/ref/heads/{self._default_branch}")
        self._base_sha = ref["object"]["sha"]

    def checkout_branch(self, branch: str) -> None:
        self._ensure_base()
        try:
            self._request("POST", f"/repos/{self.repo}/git/refs",
                          {"ref": f"refs/heads/{branch}", "sha": self._base_sha})
            self.reporter.say(f"GitHub: created branch {branch}")
        except _ApiError as e:
            if e.code == 422:  # already exists
                self.reporter.say(f"GitHub: branch {branch} exists — reusing")
            else:
                raise

    def commit_file(self, branch: str, path: str, content: str) -> None:
        existing_sha = None
        try:
            cur = self._request("GET", f"/repos/{self.repo}/contents/{path}?ref={branch}")
            existing_sha = cur.get("sha")
        except _ApiError as e:
            if e.code != 404:
                raise
        payload = {
            "message": f"Neo: draft for {path}",
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }
        if existing_sha:
            payload["sha"] = existing_sha
        self._request("PUT", f"/repos/{self.repo}/contents/{path}", payload)
        self.reporter.say(f"GitHub: committed {path} on {branch}")

    def open_pull_request(self, branch: str, title: str) -> str:
        self._ensure_base()
        owner = self.repo.split("/")[0]
        body = "Drafted by Neo. Review the proposal and sign off, or request changes."
        try:
            pr = self._request("POST", f"/repos/{self.repo}/pulls",
                               {"title": title, "head": branch,
                                "base": self._default_branch, "body": body})
            url = pr.get("html_url", "")
            self.reporter.say(f"GitHub: opened PR {url}")
            return url
        except _ApiError as e:
            if e.code == 422:  # PR may already exist for this head
                prs = self._request(
                    "GET", f"/repos/{self.repo}/pulls?head={owner}:{branch}&state=open")
                if prs:
                    url = prs[0].get("html_url", "")
                    self.reporter.say(f"GitHub: PR already open {url}")
                    return url
            raise


# --------------------------------------------------------------------------
# Claude (still a dry stub — next integration to wire)
# --------------------------------------------------------------------------


class ClaudeClient:
    """Claude acts as one of the developers: it drafts the work."""
    def __init__(self, reporter: Reporter | None = None):
        self.reporter = reporter or ConsoleReporter()

    def draft(self, request: str, skill_text: str) -> str:
        self.reporter.say("Claude: drafting with the loaded skill")
        return (
            "# DRAFT (placeholder)\n\n"
            f"Request: {request}\n\n"
            "This is where Claude's drafted proposal will appear once the "
            "Anthropic API is wired in. The loaded skill shaped this output."
        )
