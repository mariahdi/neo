"""
Dashboard Read/Write API for the Neo control panel.

- get_dashboard()  -> proposals grouped into human-facing columns
- create_request() -> create a new proposal request the loop will pick up

Lightweight on purpose: the dashboard lists many tickets, so it reads plain
Jira fields directly (summary / duedate / priority / labels) and does NOT call
Claude per ticket. Claude extraction stays in review_api for the detail view.

No Jira keys, statuses, or branch names are surfaced to the reviewer — every
column carries a clean human label and cards expose only an opaque id.
"""

import os
import requests
from base64 import b64encode

# ── Config (from env vars, same as review_api / actions_api) ──────────────────
# Optional reads: missing creds → demo mode (see review_api for the rationale).
JIRA_BASE_URL = os.environ.get("NEO_JIRA_BASE_URL")
JIRA_EMAIL    = os.environ.get("NEO_JIRA_EMAIL")
JIRA_TOKEN    = os.environ.get("NEO_JIRA_API_TOKEN")
JIRA_PROJECT  = os.environ.get("NEO_JIRA_PROJECT", "NEO")

DEMO_MODE = not all([JIRA_BASE_URL, JIRA_EMAIL, JIRA_TOKEN])

JIRA_HEADERS = {}
if not DEMO_MODE:
    JIRA_AUTH = b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    JIRA_HEADERS = {
        "Authorization": f"Basic {JIRA_AUTH}",
        "Content-Type": "application/json",
    }

# ── Jira status -> human-facing column ────────────────────────────────────────
# Order here is the order columns render on the dashboard.
COLUMNS = [
    {"key": "queued",   "label": "Queued",       "status": "To Do",
     "blurb": "Just requested — waiting for Neo."},
    {"key": "drafting", "label": "Drafting",     "status": "In Progress",
     "blurb": "Neo is drafting it."},
    {"key": "review",   "label": "Needs Review",  "status": "In Review",
     "blurb": "Ready for your sign-off."},
    {"key": "done",     "label": "Approved",     "status": "Done",
     "blurb": "Signed off and parked."},
]
_STATUS_TO_KEY = {c["status"].lower(): c["key"] for c in COLUMNS}


def _adf(text: str) -> dict:
    """Minimal Atlassian Document Format wrapper (Jira API v3 needs this)."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph",
                     "content": [{"type": "text", "text": text}]}],
    }


def _category(fields: dict) -> str:
    """HOT if the ticket is flagged urgent via labels or priority, else STD."""
    labels = [l.lower() for l in (fields.get("labels") or [])]
    if any(tag in labels for tag in ("hot", "urgent", "auto-start")):
        return "HOT"
    priority = ((fields.get("priority") or {}).get("name") or "").lower()
    if priority in ("high", "highest"):
        return "HOT"
    return "STD"


# Summary prefixes Neo gives the work it creates, one per module. The board
# and review queue surface these and nothing else, so dev/build tickets and
# project epics stay off the reviewer's screen.
_WORK_PREFIXES = ("proposal", "usafa")


def _is_neo_work(summary: str) -> bool:
    """True for a reviewer-facing Neo ticket from any enabled module.

    Neo names its work '<Module> — <title>' (e.g. 'Proposal — Red Cross',
    'USAFA — homepage banner'). This hides VOID tickets and the module epics
    ('Proposals module ...', 'USAFA module ...'), while showing the real work
    from every module.
    """
    s = (summary or "").strip().lower()
    if "void" in s:
        return False
    if s.startswith("proposals ") or s.startswith("usafa module"):
        return False  # the module epics, not actual work
    return s.startswith(_WORK_PREFIXES)


def get_dashboard() -> dict:
    """
    Return the control-panel view: columns of proposals plus a total count.

    Shape:
        {
          "total": int,
          "columns": [
            {"key", "label", "blurb", "count", "items": [
                {"id", "title", "deadline", "category"} ...
            ]},
            ...
          ]
        }
    """
    if DEMO_MODE:
        from .demo_data import demo_dashboard
        return demo_dashboard()

    statuses = ", ".join(f'"{c["status"]}"' for c in COLUMNS)
    jql = (
        f'project = {JIRA_PROJECT} AND status in ({statuses}) '
        f'ORDER BY updated DESC'
    )
    # Jira removed GET /rest/api/3/search (returns 410 Gone). Use /search/jql.
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    params = {
        "jql": jql,
        "fields": "summary,status,duedate,priority,labels",
        "maxResults": 100,
    }
    resp = requests.get(url, headers=JIRA_HEADERS, params=params)
    resp.raise_for_status()
    issues = resp.json().get("issues", [])

    buckets = {c["key"]: [] for c in COLUMNS}
    for issue in issues:
        f = issue["fields"]
        if not _is_neo_work(f.get("summary", "")):
            continue  # hide VOID / dev / epic tickets — Neo work items only
        status_name = ((f.get("status") or {}).get("name") or "").lower()
        col_key = _STATUS_TO_KEY.get(status_name)
        if col_key is None:
            continue  # status we don't show on the board
        buckets[col_key].append({
            "id": issue["key"],            # opaque to the reviewer; only used in URLs
            "title": f.get("summary", "Untitled proposal"),
            "deadline": f.get("duedate"),  # ISO date string or None
            "category": _category(f),
        })

    columns = [{
        "key": c["key"],
        "label": c["label"],
        "blurb": c["blurb"],
        "count": len(buckets[c["key"]]),
        "items": buckets[c["key"]],
    } for c in COLUMNS]

    return {"total": sum(len(buckets[c["key"]]) for c in COLUMNS), "columns": columns}


def create_request(text: str) -> str:
    """
    Create a new proposal request from typed text / a pasted transcript.

    Lands in the project's default 'To Do' status so the Neo loop picks it up,
    drafts it, and it flows back through review. Returns the opaque id.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty request")

    if DEMO_MODE:
        # No Jira to write to — accept the request so the flow completes.
        return "NEO-DEMO"

    # First non-empty line becomes the title; full text is the description.
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), text)
    summary = first_line[:80]
    if not summary.lower().startswith("proposal"):
        summary = f"Proposal — {summary}"

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT},
            "summary": summary,
            "issuetype": {"name": "Task"},
            "description": _adf(text),
        }
    }
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    resp = requests.post(url, headers=JIRA_HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json().get("key", "?")


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    print(json.dumps(get_dashboard(), indent=2))
