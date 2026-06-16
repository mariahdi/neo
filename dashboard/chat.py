"""The chat bar's brain.

Turns a typed request ("I need a proposal for USAFA for website development")
into real work: it figures out which module owns the request, opens a Jira
ticket, and kicks off the draft through the existing Neo loop — the same loop
`python -m neo --live` runs. Nothing here is new orchestration; it's the web
front door onto the machinery that already exists.

Without live credentials the whole thing runs in demo mode: it still tells you
which module it picked and what it *would* do, but makes no network calls.
"""
from __future__ import annotations

import os

from neo.config import Config
from neo.loop import NeoLoop
from neo.neo_types import Category, State, WorkItem
from neo.router import route

# How each module wants its Jira summary to read. The board only surfaces
# tickets whose summary starts with "Proposal", so proposals get that prefix;
# other modules get their own clear label.
_SUMMARY_PREFIX = {
    "proposals": "Proposal — ",
    "usafa": "USAFA — ",
}

# Friendly module names for the chat reply.
_MODULE_LABEL = {
    "proposals": "proposals",
    "usafa": "USAFA web-dev",
    "landlord": "landlord",
    "airforce_web": "Air Force web",
}

_JIRA_PROJECT = os.environ.get("NEO_JIRA_PROJECT", "NEO")

# Cache the live-capability probe so we don't rebuild clients on every keystroke.
_live_error: str | None = None
_probed = False


def _config() -> Config:
    return Config.load()


def _new_loop() -> NeoLoop:
    """A fresh live loop (real Jira / GitHub / Claude clients)."""
    return NeoLoop(_config(), live=True)


def is_live() -> bool:
    """True when every credential the loop needs is present.

    Probes once by trying to build the live clients; they raise RuntimeError
    when a NEO_* var is missing. Cached so the chat bar stays snappy.
    """
    global _probed, _live_error
    if not _probed:
        try:
            _new_loop()
            _live_error = None
        except Exception as e:  # RuntimeError from a missing credential
            _live_error = str(e)
        _probed = True
    return _live_error is None


def detect_module(text: str) -> str:
    """Which module owns this request? Uses Neo's own keyword router so the
    web front door routes exactly like the CLI does."""
    probe = WorkItem(key="?", title=text[:80], request=text, module="")
    route(probe, _config().enabled_modules)
    return probe.module or "proposals"  # default to the proof-of-concept module


def _summary_for(module: str, text: str) -> str:
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), text)
    body = first_line[:80]
    prefix = _SUMMARY_PREFIX.get(module, "")
    if prefix and not body.lower().startswith(prefix.split()[0].lower()):
        return f"{prefix}{body}"
    return body


def start_request(text: str) -> dict:
    """Open the ticket (fast) and report what happened.

    Returns {ok, ticket, module, module_label, title, demo, message}. The slow
    part — drafting and opening the PR — is handed off to run_draft() in the
    background so the chat replies immediately.
    """
    text = (text or "").strip()
    if not text:
        return {"ok": False, "message": "Type a request first — e.g. "
                "“I need a proposal for USAFA for website development.”"}

    module = detect_module(text)
    label = _MODULE_LABEL.get(module, module)
    title = _summary_for(module, text)

    if not is_live():
        return {
            "ok": True,
            "demo": True,
            "ticket": "NEO-DEMO",
            "module": module,
            "module_label": label,
            "title": title,
            "message": (
                f"Got it — this routes to the {label} module. In demo mode "
                "I don’t touch Jira or GitHub, so no ticket was created. "
                "Set the NEO_* keys to go live and I’ll open the ticket and "
                "start the draft."
            ),
        }

    # Live: create the ticket now so we can hand back a real key, then draft
    # in the background.
    loop = _new_loop()
    key = loop.ctx.jira.create_issue(
        project=_JIRA_PROJECT, summary=title, issue_type="Task", description=text
    )
    return {
        "ok": True,
        "demo": False,
        "ticket": key,
        "module": module,
        "module_label": label,
        "title": title,
        "message": f"Got it — created {key} and starting the {label} draft.",
    }


def run_draft(ticket: str, title: str, text: str, module: str) -> None:
    """Drive the ticket through draft → PR → In Review (slow; runs in the
    background). Mirrors one tick of the live Neo loop for a single item."""
    try:
        loop = _new_loop()
        item = WorkItem(
            key=ticket,
            title=title,
            request=text,
            module=module,
            category=Category.HOT,  # chat requests are an explicit "go"
        )
        # force_start so even a standard-category request drafts right away.
        loop.tick([item], force_start=True)
    except Exception as e:  # never let a background failure crash the server
        print(f"[dashboard.chat] draft for {ticket} failed: {e}")
        # Park it back in To Do so it's visible and retryable, best-effort.
        try:
            _new_loop().ctx.jira.transition(ticket, State.TODO.value)
        except Exception:
            pass
