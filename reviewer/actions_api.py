"""
NEO-13: Approve / Request Changes / Re-prompt Actions
Wires the reviewer decision buttons to real backend operations:
- Approve        → Jira ticket → Done (parked for owner sign-off)
- Request Changes → comment on PR, Jira → In Progress, trigger Claude regen
- Re-prompt       → same as Request Changes but with new context signal
No Git/Jira jargon exposed to the reviewer.
"""

import os
import json
import requests
from base64 import b64encode

# ── Config ────────────────────────────────────────────────────────────────────
# Optional reads: missing creds → demo mode (see review_api for the rationale).
JIRA_BASE_URL = os.environ.get("NEO_JIRA_BASE_URL")
JIRA_EMAIL    = os.environ.get("NEO_JIRA_EMAIL")
JIRA_TOKEN    = os.environ.get("NEO_JIRA_API_TOKEN")
GITHUB_TOKEN  = os.environ.get("NEO_GITHUB_TOKEN")
GITHUB_REPO   = os.environ.get("NEO_GITHUB_REPO")  # e.g. "mariahdi/neo"
ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")

DEMO_MODE = not all([JIRA_BASE_URL, JIRA_EMAIL, JIRA_TOKEN,
                     GITHUB_TOKEN, GITHUB_REPO, ANTHROPIC_KEY])

JIRA_HEADERS = {}
GITHUB_HEADERS = {}
if not DEMO_MODE:
    JIRA_AUTH = b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    JIRA_HEADERS = {
        "Authorization": f"Basic {JIRA_AUTH}",
        "Content-Type": "application/json",
    }
    GITHUB_HEADERS = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

# ── Jira Transition IDs (from your board) ────────────────────────────────────
TRANSITION_IN_PROGRESS = "21"
TRANSITION_DONE        = "41"

# ── Helper: find open PR for a ticket ────────────────────────────────────────
def _find_pr(ticket_key: str) -> dict | None:
    """Find the open GitHub PR for this ticket by branch name convention."""
    branch = f"feature/{ticket_key}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls"
    params = {"state": "open", "head": f"{GITHUB_REPO.split('/')[0]}:{branch}"}
    resp = requests.get(url, headers=GITHUB_HEADERS, params=params)
    if resp.status_code != 200:
        return None
    prs = resp.json()
    return prs[0] if prs else None


def _transition_jira(ticket_key: str, transition_id: str) -> bool:
    """Move a Jira ticket to a new status."""
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket_key}/transitions"
    body = {"transition": {"id": transition_id}}
    resp = requests.post(url, headers=JIRA_HEADERS, json=body)
    return resp.status_code in (200, 204)


def _post_pr_comment(pr_number: int, body: str) -> bool:
    """Post a comment on a GitHub PR."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/comments"
    resp = requests.post(url, headers=GITHUB_HEADERS, json={"body": body})
    return resp.status_code == 201


def _trigger_claude_regen(ticket_key: str, feedback: str, mode: str) -> str:
    """
    Ask Claude to revise the proposal given the reviewer's feedback.
    Returns the new draft text.
    mode: "changes" | "reprompt"
    """
    verb = "rewrite" if mode == "reprompt" else "revise"
    prompt = f"""You are Neo, an AI proposal writer. A reviewer has asked you to {verb} a proposal.

Ticket: {ticket_key}
Reviewer feedback: {feedback}

Please {verb} the proposal incorporating this feedback. Return only the revised proposal text, no preamble."""

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()


def _update_pr_with_new_draft(ticket_key: str, new_draft: str, pr_number: int) -> bool:
    """Commit the revised draft to the PR branch."""
    branch = f"feature/{ticket_key}"
    file_path = f"proposals/{ticket_key}.md"

    # Get current file SHA (needed to update)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    params = {"ref": branch}
    resp = requests.get(url, headers=GITHUB_HEADERS, params=params)
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    # Commit updated draft
    import base64
    body = {
        "message": f"{ticket_key}: revise proposal per reviewer feedback",
        "content": base64.b64encode(new_draft.encode()).decode(),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha

    resp = requests.put(url, headers=GITHUB_HEADERS, json=body)
    return resp.status_code in (200, 201)


# ── Public Actions ────────────────────────────────────────────────────────────

def approve(proposal_id: str) -> dict:
    """
    Reviewer approves — park the ticket for owner sign-off.
    Jira → Done. PR stays open until owner merges.
    Returns {"ok": bool, "message": str}
    """
    if DEMO_MODE:
        return {"ok": True,
                "message": "Approved! (demo mode — nothing was sent to Jira or GitHub)"}

    ok = _transition_jira(proposal_id, TRANSITION_DONE)

    pr = _find_pr(proposal_id)
    if pr:
        _post_pr_comment(
            pr["number"],
            f"✅ **Approved by reviewer.** Parked for owner sign-off. PR will merge on owner approval."
        )

    return {
        "ok": ok,
        "message": "Approved! Parked for owner sign-off." if ok else "Jira transition failed — check your token."
    }


def request_changes(proposal_id: str, feedback: str, mode: str = "changes") -> dict:
    """
    Reviewer requests changes or re-prompts Claude.
    - Posts feedback comment on PR
    - Moves Jira → In Progress
    - Triggers Claude to regenerate and commits revised draft
    Returns {"ok": bool, "message": str}
    """
    if DEMO_MODE:
        return {"ok": True,
                "message": "Feedback noted! (demo mode — nothing was sent to Claude or GitHub)",
                "details": {}}

    results = {}

    # 1. Move Jira back to In Progress
    results["jira"] = _transition_jira(proposal_id, TRANSITION_IN_PROGRESS)

    # 2. Find the PR
    pr = _find_pr(proposal_id)
    if pr:
        # 3. Post reviewer feedback as PR comment
        label = "🔄 Re-prompt" if mode == "reprompt" else "✏️ Changes requested"
        comment = f"{label} by reviewer:\n\n> {feedback}"
        results["comment"] = _post_pr_comment(pr["number"], comment)

        # 4. Trigger Claude regen and commit revised draft
        try:
            new_draft = _trigger_claude_regen(proposal_id, feedback, mode)
            results["regen"] = _update_pr_with_new_draft(proposal_id, new_draft, pr["number"])
            if results["regen"]:
                _post_pr_comment(
                    pr["number"],
                    f"🤖 **Claude has revised the proposal.** New draft committed to `feature/{proposal_id}`."
                )
        except Exception as e:
            print(f"[NEO-13] Claude regen failed for {proposal_id}: {e}")
            results["regen"] = False
    else:
        results["comment"] = False
        results["regen"] = False
        print(f"[NEO-13] No open PR found for {proposal_id}")

    ok = results["jira"]
    message = "Feedback sent to Claude — it will revise and resubmit." if ok else "Something went wrong — check logs."
    return {"ok": ok, "message": message, "details": results}


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "approve"
    ticket = sys.argv[2] if len(sys.argv) > 2 else "NEO-2"

    if action == "approve":
        print(json.dumps(approve(ticket), indent=2))
    elif action == "changes":
        feedback = sys.argv[3] if len(sys.argv) > 3 else "Please add a budget breakdown."
        print(json.dumps(request_changes(ticket, feedback, "changes"), indent=2))
    elif action == "reprompt":
        feedback = sys.argv[3] if len(sys.argv) > 3 else "Rewrite with more emphasis on impact."
        print(json.dumps(request_changes(ticket, feedback, "reprompt"), indent=2))
