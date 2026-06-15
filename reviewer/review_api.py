"""
NEO-12: Review Read API
Pulls In Review tickets from Jira and uses Claude to extract clean reviewer-friendly data.
No Jira keys, branch names, or raw API jargon leaks through to the caller.
"""

import os
import json
import requests
from base64 import b64encode

# ── Config (from env vars) ────────────────────────────────────────────────────
# Read optionally: if any key is missing we fall back to demo data instead of
# crashing on import, so the app can be shown end to end without live creds.
JIRA_BASE_URL = os.environ.get("NEO_JIRA_BASE_URL")
JIRA_EMAIL    = os.environ.get("NEO_JIRA_EMAIL")
JIRA_TOKEN    = os.environ.get("NEO_JIRA_API_TOKEN")
ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")

DEMO_MODE = not all([JIRA_BASE_URL, JIRA_EMAIL, JIRA_TOKEN, ANTHROPIC_KEY])

JIRA_HEADERS = {}
if not DEMO_MODE:
    JIRA_AUTH = b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    JIRA_HEADERS = {
        "Authorization": f"Basic {JIRA_AUTH}",
        "Content-Type": "application/json",
    }

# ── Step 1: Fetch In Review tickets from Jira ─────────────────────────────────
def fetch_in_review_tickets() -> list[dict]:
    """Return raw Jira issues currently In Review."""
    jql = 'project = NEO AND status = "In Review" ORDER BY created DESC'
    # Jira removed GET /rest/api/3/search (returns 410 Gone). Use the enhanced
    # /search/jql endpoint — same query params, response still has "issues".
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"
    params = {
        "jql": jql,
        "fields": "summary,description,assignee,priority,labels,duedate",
        "maxResults": 50,
    }
    resp = requests.get(url, headers=JIRA_HEADERS, params=params)
    resp.raise_for_status()
    return resp.json().get("issues", [])


# ── Step 2: Use Claude to extract clean fields from description ───────────────
def extract_fields_with_claude(ticket_key: str, summary: str, description_text: str) -> dict:
    """
    Ask Claude to pull reviewer-friendly fields from the raw ticket description.
    Returns a plain dict — no Jira keys, no branch names.
    """
    prompt = f"""You are reading a Jira ticket for a proposals system. 
Extract the following fields from the ticket and return ONLY a JSON object, no preamble, no markdown fences.

Fields to extract:
- title: short human-readable proposal title (use the summary if nothing better)
- sender: the person or org requesting the proposal (could be a name, org, or contact)
- amount: funding amount as a string, e.g. "$2,500,000" (null if not found)
- deadline: deadline date as a string, e.g. "Sep 15, 2026" (null if not found)  
- funder: who the proposal is addressed to, e.g. "USAID" (null if not found)
- category: "HOT" if the ticket mentions hot/urgent/auto-start, otherwise "STD"
- draft: the proposal draft text if present, otherwise null
- summary: one sentence describing what this proposal is for

Ticket key: {ticket_key}
Summary: {summary}
Description:
{description_text}

Return only a JSON object with those exact keys."""

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
    raw = resp.json()["content"][0]["text"].strip()

    # Strip markdown fences if Claude added them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    fields = json.loads(raw.strip())
    fields["id"] = ticket_key  # opaque ID for the reviewer — no branch info
    return fields


# ── Step 3: Public function — the only thing the web app calls ────────────────
def get_review_queue() -> list[dict]:
    """
    Returns a clean list of proposals ready for reviewer display.
    Each item has: id, title, sender, amount, deadline, funder, category, draft, summary.
    No Jira keys, branch names, or raw API data exposed.
    """
    if DEMO_MODE:
        from .demo_data import demo_review_queue
        return demo_review_queue()

    tickets = fetch_in_review_tickets()
    results = []

    for ticket in tickets:
        key = ticket["key"]
        summary = ticket["fields"].get("summary", "")

        # Flatten description to plain text
        desc_obj = ticket["fields"].get("description") or {}
        description_text = _flatten_adf(desc_obj)

        try:
            fields = extract_fields_with_claude(key, summary, description_text)
            results.append(fields)
        except Exception as e:
            # Don't crash the whole queue if one ticket fails
            print(f"[NEO-12] Failed to extract fields for {key}: {e}")
            results.append({
                "id": key,
                "title": summary,
                "sender": "Unknown",
                "amount": None,
                "deadline": None,
                "funder": None,
                "category": "STD",
                "draft": None,
                "summary": summary,
            })

    return results


def get_proposal(proposal_id: str) -> dict | None:
    """
    Fetch a single proposal by its opaque ID (which happens to be the Jira key).
    Returns clean reviewer-friendly dict, or None if not found.
    """
    if DEMO_MODE:
        from .demo_data import demo_get_proposal
        return demo_get_proposal(proposal_id)

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{proposal_id}"
    params = {"fields": "summary,description,assignee,priority,labels,duedate"}
    resp = requests.get(url, headers=JIRA_HEADERS, params=params)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    ticket = resp.json()
    summary = ticket["fields"].get("summary", "")
    desc_obj = ticket["fields"].get("description") or {}
    description_text = _flatten_adf(desc_obj)

    return extract_fields_with_claude(proposal_id, summary, description_text)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _flatten_adf(adf: dict) -> str:
    """Recursively flatten Atlassian Document Format to plain text."""
    if not adf:
        return ""
    parts = []
    node_type = adf.get("type", "")

    if node_type == "text":
        parts.append(adf.get("text", ""))
    elif node_type in ("paragraph", "heading", "listItem", "bulletList", "orderedList", "blockquote"):
        for child in adf.get("content", []):
            parts.append(_flatten_adf(child))
        parts.append("\n")
    elif node_type == "table":
        for row in adf.get("content", []):
            cells = [_flatten_adf(cell).strip() for cell in row.get("content", [])]
            parts.append(" | ".join(cells))
            parts.append("\n")
    elif node_type == "tableCell" or node_type == "tableHeader":
        for child in adf.get("content", []):
            parts.append(_flatten_adf(child))
    elif "content" in adf:
        for child in adf["content"]:
            parts.append(_flatten_adf(child))

    return "".join(parts)


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching In Review queue...")
    queue = get_review_queue()
    print(json.dumps(queue, indent=2))
