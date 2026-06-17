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
import re

import requests

from neo.config import Config
from neo.loop import NeoLoop
from neo.neo_types import Category, State, WorkItem
from neo.router import route

ANTHROPIC_KEY = os.environ.get("NEO_ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("NEO_ANTHROPIC_MODEL", "claude-sonnet-4-6")

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


def start_request(text: str, module: str | None = None) -> dict:
    """Open the ticket (fast) and report what happened.

    Returns {ok, ticket, module, module_label, title, demo, message}. The slow
    part — drafting and opening the PR — is handed off to run_draft() in the
    background so the chat replies immediately. Pass `module` to force a target
    (e.g. the USAFA page routes every request to "usafa"); otherwise the module
    is detected from the text.
    """
    text = (text or "").strip()
    if not text:
        return {"ok": False, "message": "Type a request first — e.g. "
                "“I need a proposal for USAFA for website development.”"}

    module = module or detect_module(text)
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


# ── Intent routing ────────────────────────────────────────────────────────────
# The top-level "Ask Neo" assistant routes by intent across modules, instead of
# defaulting everything to proposals.
_INTENTS = ("wins", "goals", "proposal", "usafa", "none")


def _classify_keyword(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ("proposal", "rfp", "grant", "bid", "red cross")):
        return "proposal"
    if any(k in t for k in ("usafa", "air force academy", "academy site", "academy website")):
        return "usafa"
    if any(k in t for k in ("win", "accomplish", "today i", "got done", "i made", "i finished", "proud")):
        return "wins"
    if re.search(r"\d", t) and any(k in t for k in ("weigh", "lbs", "pounds", "goal", "saved", "read", "progress")):
        return "goals"
    return "none"


def classify(text: str) -> str:
    """Which module/action this request is for. Uses Claude when available, with
    a keyword fallback."""
    if not ANTHROPIC_KEY:
        return _classify_keyword(text)
    prompt = (
        "Classify the user's request into exactly one of: wins, goals, proposal, usafa, none.\n"
        "- wins: logging accomplishments or describing their day "
        "(\"track my wins\", \"today I made the call and went to the gym\")\n"
        "- goals: reporting measurable progress toward a goal "
        "(\"weighed myself, 182\", \"read 2 more books\")\n"
        "- proposal: asking to draft a proposal, grant, bid, or funding document\n"
        "- usafa: a change to the USAFA / Air Force Academy website — ONLY if it "
        "explicitly names USAFA or the Air Force Academy\n"
        "- none: anything else — INCLUDING editing a personal page or module "
        "(About / About Me, Body, budget, Stocks, Trips, Wealth, Wellness); those "
        "are edited on their own pages, not by this assistant\n"
        f'Request: "{text}"\n'
        "Reply with only the one word."
    )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": ANTHROPIC_MODEL, "max_tokens": 8,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=20,
        )
        resp.raise_for_status()
        word = re.sub(r"[^a-z]", "", resp.json()["content"][0]["text"].strip().lower())
        return word if word in _INTENTS else "none"
    except Exception as e:
        print(f"[chat] classify failed ({e}); using keywords")
        return _classify_keyword(text)


def handle(text: str, background) -> dict:
    """Route one assistant request by intent: wins/goals log to their modules;
    proposal/usafa open a ticket + draft; anything else asks to clarify."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "message": "Type a request first."}

    intent = classify(text)
    if intent == "wins":
        from . import wins
        return wins.log_from_text(text)
    if intent == "goals":
        from . import goals
        return goals.log_from_text(text)
    if intent in ("proposal", "usafa"):
        result = start_request(text)
        if result.get("ok") and not result.get("demo"):
            background.add_task(run_draft, result["ticket"], result["title"], text, result["module"])
        return result
    return {"ok": True, "message": (
        "I can log a win, update a goal, or draft a proposal / USAFA task — "
        "tell me which, or use a module's own box on its page."
    )}
