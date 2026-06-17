"""Neo — the unified dashboard.

One FastAPI app, one page. The chat bar opens tickets and kicks off drafts;
the live board shows everything in flight; In Review proposals appear as full
cards with Approve / Request Changes / Re-prompt right there; module widgets
summarize the system. It replaces the separate reviewer app and static
dashboard, reusing the existing backend APIs unchanged.

    uvicorn dashboard.main:app --reload

With no NEO_* credentials set it runs in demo mode (sample data). Set the
Jira / GitHub / Anthropic keys to go live.

When deployed to a public URL, set DASHBOARD_USER and DASHBOARD_PASS to put a
login screen in front of the whole app (see dashboard/auth.py and
docs/DEPLOY.md). Leaving them unset — the local/demo default — means no login.
"""
from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from neo.config import Config
from reviewer.actions_api import approve as do_approve
from reviewer.actions_api import request_changes as do_request_changes
from reviewer.dashboard_api import DEMO_MODE as BOARD_DEMO
from reviewer.dashboard_api import get_dashboard
from reviewer.review_api import DEMO_MODE as REVIEW_DEMO
from reviewer.review_api import _fetch_draft_from_github, get_review_queue

from . import auth, chat, profile, theme
from .about import router as about_router
from .body import router as body_router
from .wealth import router as wealth_router
from .goals import router as goals_router
from .modules_api import router as modules_router
from .nominal import router as nominal_router
from .stocks import router as stocks_router
from .wins import router as wins_router

app = FastAPI(title="Neo", version="1.0.0")

# Persistent session login (NEO-33): a /login screen + signed session cookie
# instead of a re-prompting Basic-Auth popup. Enforced only when
# DASHBOARD_USER/DASHBOARD_PASS are set; local/demo runs stay open.
app.add_middleware(auth.SessionMiddleware)
app.include_router(auth.router)

# Module pages (About Me, Stocks, and more to come) live in their own routers.
app.include_router(about_router)
app.include_router(stocks_router)
app.include_router(goals_router)
app.include_router(wins_router)
app.include_router(nominal_router)
app.include_router(body_router)
app.include_router(wealth_router)
app.include_router(modules_router)

# Board column keys (from dashboard_api.COLUMNS) -> the canonical labels the
# unified dashboard shows. Same four columns the prompt asks for.
_COLUMN_LABELS = {
    "queued": "To Do",
    "drafting": "In Progress",
    "review": "In Review",
    "done": "Done",
}


def _module_widgets(board: dict) -> list[dict]:
    """Summary cards for each module. Counts come from the live board where we
    have them; Calendar and Landlord are placeholders for modules not built
    yet."""
    enabled = set(Config.load().enabled_modules)
    by_key = {c["key"]: c for c in board["columns"]}
    in_review = by_key.get("review", {}).get("count", 0)
    in_flight = board.get("total", 0)

    return [
        {
            "key": "tasks",
            "label": "Tasks",
            "stat": str(in_flight),
            "note": f"{in_review} awaiting review" if in_flight else "Nothing in flight",
            "status": "live",
        },
        {
            "key": "usafa",
            "label": "USAFA",
            "stat": "On" if "usafa" in enabled else "Off",
            "note": "Web-dev module" + (" · enabled" if "usafa" in enabled else " · disabled"),
            "status": "live" if "usafa" in enabled else "off",
        },
        {
            "key": "calendar",
            "label": "Calendar",
            "stat": "—",
            "note": "Coming soon",
            "status": "placeholder",
        },
        {
            "key": "landlord",
            "label": "Landlord",
            "stat": "—",
            "note": "Coming soon",
            "status": "placeholder",
        },
    ]


def _reviews_with_drafts() -> list[dict]:
    """In Review proposals, each with its draft text ready to show inline.

    The queue extracts ticket fields, but the real draft lives in the PR, not
    the Jira description — so for any review missing a draft we pull it from
    GitHub (same source the old detail view used). Demo data ships its own
    drafts, so we only reach out when live.
    """
    reviews = get_review_queue()
    if not REVIEW_DEMO:
        for r in reviews:
            if not (r.get("draft") or "").strip():
                draft = _fetch_draft_from_github(r["id"])
                if draft:
                    r["draft"] = draft
    return reviews


@app.get("/api/state")
async def state() -> JSONResponse:
    """Everything the page renders, in one payload. Polled every 30s."""
    board = get_dashboard()
    for col in board["columns"]:
        col["label"] = _COLUMN_LABELS.get(col["key"], col["label"])
    return JSONResponse({
        "demo": BOARD_DEMO,
        "board": board,
        "reviews": _reviews_with_drafts(),
        "modules": _module_widgets(board),
    })


class ChatIn(BaseModel):
    text: str


@app.post("/api/chat")
async def chat_send(body: ChatIn, background: BackgroundTasks) -> JSONResponse:
    """Chat bar: route the request, open a ticket, kick off the draft."""
    result = chat.start_request(body.text)
    if result.get("ok") and not result.get("demo"):
        # Draft + open PR + move to In Review, off the request thread.
        background.add_task(
            chat.run_draft,
            result["ticket"], result["title"], body.text, result["module"],
        )
    return JSONResponse(result)


class ChangesIn(BaseModel):
    feedback: str
    mode: str = "changes"  # "changes" | "reprompt"


@app.post("/api/reviews/{proposal_id}/approve")
async def review_approve(proposal_id: str) -> JSONResponse:
    return JSONResponse(do_approve(proposal_id))


@app.post("/api/reviews/{proposal_id}/changes")
async def review_changes(proposal_id: str, body: ChangesIn) -> JSONResponse:
    return JSONResponse(do_request_changes(proposal_id, body.feedback, body.mode))


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    # Nav is rendered per-request so module gating + the "new modules" badge
    # stay live (the rest of the shell is baked once at import).
    return HTMLResponse(PAGE.replace("<!--NAV-->", theme.nav("dashboard")))


# ── The page ──────────────────────────────────────────────────────────────────
# Static shell: all data arrives from /api/state, so there's nothing to
# server-render here. Kept as one plain string (no f-string) so CSS/JS braces
# stay literal.
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><!--TITLE--></title>
<!--FONTS-->
<style>
  /*ROOTCSS*/
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--font-body);
    background: radial-gradient(1200px 600px at 70% -10%, var(--bg-glow) 0%, var(--bg) 55%) fixed;
    color: var(--text);
    min-height: 100vh;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  h1, h2, h3, .bebas {
    font-family: var(--font-head);
    font-weight: 400;
    letter-spacing: 0.04em;
  }
  a { color: inherit; }

  /* Top bar */
  header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 32px;
    border-bottom: 1px solid var(--line-soft);
    background: rgba(10,14,26,0.7);
    backdrop-filter: blur(6px);
    position: sticky; top: 0; z-index: 20;
  }
  .brand { font-size: 30px; letter-spacing: 0.12em; }
  .brand b { color: var(--gold); font-weight: 400; }
  .brand small {
    display: block; font-family: var(--font-body); font-size: 10px;
    letter-spacing: 0.22em; text-transform: uppercase; color: var(--muted);
    margin-top: -4px;
  }
  .who { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }
  .brand { text-decoration: none; }
  .topnav { display: flex; gap: 22px; margin-right: auto; margin-left: 10px; }
  .topnav a { font-size: 12px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); text-decoration: none; padding: 6px 0; }
  .topnav a:hover, .topnav a.active { color: var(--gold); }
  .nav-badge { display: inline-block; background: var(--gold); color: var(--on-gold); font-size: 9px; font-weight: 700; border-radius: 10px; padding: 0 5px; margin-left: 5px; vertical-align: 1px; }
  .logout { background: none; border: 1px solid var(--line); color: var(--muted); font-family: inherit; font-size: 10.5px; letter-spacing: 0.1em; text-transform: uppercase; cursor: pointer; border-radius: 8px; padding: 5px 11px; }
  .logout:hover { border-color: var(--gold-line); color: var(--gold); }
  /*EXTRA_CSS*/

  .demo-banner {
    display: none;
    background: var(--gold-soft); border-bottom: 1px solid var(--gold-line);
    color: var(--gold); font-size: 12px; letter-spacing: 0.04em;
    text-align: center; padding: 8px 16px;
  }
  .demo-banner.show { display: block; }
  .demo-banner b { color: #e7c766; }

  main { max-width: 1240px; margin: 0 auto; padding: 28px 32px 64px; }
  .section-label {
    font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase;
    color: var(--gold); margin-bottom: 12px; font-weight: 600;
  }

  /* Chat bar */
  .chat {
    background: linear-gradient(180deg, var(--panel-2), var(--panel));
    border: 1px solid var(--line); border-radius: 14px;
    padding: 18px 18px 16px; margin-bottom: 28px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.35);
  }
  .chat h2 { font-size: 22px; letter-spacing: 0.06em; }
  .chat .hint { font-size: 12.5px; color: var(--muted); margin: 2px 0 14px; }
  .chat-row { display: flex; gap: 10px; }
  #chat-input {
    flex: 1; background: var(--field); border: 1px solid var(--line);
    border-radius: 10px; color: var(--text); font-family: inherit;
    font-size: 14px; padding: 13px 15px; resize: none;
  }
  #chat-input:focus { outline: none; border-color: var(--gold-line); }
  #chat-input::placeholder { color: #5d6b8c; }
  .btn {
    border: 1px solid var(--line); background: var(--btn-bg); color: var(--text);
    font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
    border-radius: 10px; padding: 11px 18px; transition: all 0.15s;
    letter-spacing: 0.02em; white-space: nowrap;
  }
  .btn:hover { border-color: var(--gold-line); color: var(--gold); }
  .btn:disabled { opacity: 0.5; cursor: default; }
  .btn-gold { background: var(--gold); border-color: var(--gold); color: var(--on-gold); }
  .btn-gold:hover { background: var(--gold-hover); border-color: var(--gold-hover); color: var(--on-gold); }
  .btn-sm { padding: 7px 12px; font-size: 12px; }
  .btn-mic { font-size: 16px; padding: 11px 14px; line-height: 1; }
  .btn-mic[hidden] { display: none; }
  .btn-mic.listening {
    background: var(--gold); border-color: var(--gold); color: var(--on-gold);
    animation: mic-pulse 1.3s infinite;
  }
  @keyframes mic-pulse {
    0%   { box-shadow: 0 0 0 0 rgba(200,168,75,0.5); }
    70%  { box-shadow: 0 0 0 11px rgba(200,168,75,0); }
    100% { box-shadow: 0 0 0 0 rgba(200,168,75,0); }
  }
  .voice-status { display: none; margin-top: 11px; font-size: 12.5px; color: var(--gold); letter-spacing: 0.03em; }
  .voice-status.show { display: block; }
  #chat-reply {
    display: none; margin-top: 14px; padding: 12px 14px; border-radius: 10px;
    background: var(--gold-soft); border: 1px solid var(--gold-line);
    font-size: 13.5px; color: #f0e6c8;
  }
  #chat-reply.show { display: block; }
  #chat-reply.err { background: rgba(217,138,58,0.12); border-color: rgba(217,138,58,0.5); color: #f0cda0; }

  /* Module widgets */
  .widgets { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 30px; }
  @media (max-width: 820px) { .widgets { grid-template-columns: repeat(2, 1fr); } }
  .widget {
    background: var(--panel); border: 1px solid var(--line-soft);
    border-radius: 12px; padding: 16px 16px 14px; position: relative; overflow: hidden;
  }
  .widget::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--gold);
  }
  .widget.off::before, .widget.placeholder::before { background: var(--line); }
  .widget .wlabel { font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }
  .widget .wstat { font-family: 'Bebas Neue', sans-serif; font-size: 38px; line-height: 1; margin: 6px 0 4px; color: var(--gold); }
  .widget.off .wstat, .widget.placeholder .wstat { color: #4f5d7e; }
  .widget .wnote { font-size: 11.5px; color: var(--muted); }

  /* Board */
  .board { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; align-items: start; margin-bottom: 34px; }
  @media (max-width: 900px) { .board { grid-template-columns: repeat(2, 1fr); } }
  .col { background: var(--bg-2); border: 1px solid var(--line-soft); border-radius: 12px; padding: 13px; }
  .col-head { display: flex; align-items: center; justify-content: space-between; }
  .col-head h3 { font-size: 16px; letter-spacing: 0.08em; }
  .col-count { font-size: 11px; font-weight: 700; color: var(--on-gold); background: var(--gold); border-radius: 20px; padding: 1px 9px; }
  .col-blurb { font-size: 11px; color: #5f6d8e; margin: 4px 0 11px; }
  .mini {
    display: block; background: var(--panel); border: 1px solid var(--line-soft);
    border-radius: 9px; padding: 10px 11px; margin-bottom: 8px; cursor: default;
    transition: border-color 0.15s;
  }
  .mini.clickable { cursor: pointer; }
  .mini.clickable:hover { border-color: var(--gold-line); }
  .mini-title { font-size: 12.5px; font-weight: 600; line-height: 1.35; }
  .mini-meta { font-size: 11px; color: var(--muted); margin-top: 6px; display: flex; align-items: center; gap: 7px; }
  .dot-hot { width: 7px; height: 7px; border-radius: 50%; background: var(--hot); display: inline-block; }
  .col-empty { font-size: 11px; color: #45506e; font-style: italic; padding: 5px 2px; }

  /* In Review cards */
  .review { background: linear-gradient(180deg, var(--panel-2), var(--panel)); border: 1px solid var(--line); border-radius: 14px; padding: 20px; margin-bottom: 16px; }
  .review-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; flex-wrap: wrap; border-bottom: 1px solid var(--line-soft); padding-bottom: 14px; margin-bottom: 14px; }
  .review-head h3 { font-size: 21px; letter-spacing: 0.03em; }
  .review-head .meta { font-size: 12px; color: var(--muted); margin-top: 5px; }
  .tag { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; border-radius: 20px; padding: 3px 10px; }
  .tag-hot { background: var(--hot); color: var(--on-gold); }
  .tag-std { background: #1c2741; border: 1px solid var(--line); color: var(--muted); }
  .draft {
    background: #0b1120; border: 1px solid var(--line-soft); border-radius: 10px;
    padding: 16px 18px; font-size: 13px; line-height: 1.75; color: #cdd5e8;
    white-space: pre-wrap; max-height: 320px; overflow-y: auto; margin-bottom: 16px;
  }
  .draft-label { font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--gold); margin-bottom: 9px; }
  .actions { display: flex; gap: 9px; flex-wrap: wrap; }
  .feedback { display: none; margin-top: 12px; }
  .feedback.show { display: block; }
  .feedback textarea {
    width: 100%; min-height: 92px; background: var(--field); border: 1px solid var(--line);
    border-radius: 10px; color: var(--text); font-family: inherit; font-size: 13px;
    padding: 12px; resize: vertical; margin-bottom: 10px;
  }
  .feedback textarea:focus { outline: none; border-color: var(--gold-line); }
  .review-result { font-size: 12.5px; color: var(--gold); margin-top: 10px; display: none; }
  .review-result.show { display: block; }
  .empty-reviews { color: #56638a; font-style: italic; font-size: 13px; padding: 18px 2px; }
  .loading { color: var(--muted); font-size: 13px; padding: 10px 2px; }
</style>
</head>
<body>
<!--NAV-->
<div id="demo-banner" class="demo-banner">
  <b>DEMO MODE</b> · showing sample data — set the Jira / GitHub / Anthropic keys to go live.
</div>

<main>
  <!-- Chat -->
  <section class="chat">
    <h2>Ask Neo</h2>
    <p class="hint">Type a request — or tap the mic to speak — and Neo figures out the module, opens the ticket, and starts the draft.</p>
    <form id="chat-form" class="chat-row">
      <textarea id="chat-input" rows="1" placeholder="e.g. I need a proposal for USAFA for website development"></textarea>
      <button type="button" id="chat-mic" class="btn btn-mic" aria-label="Speak your request" title="Speak your request">🎙</button>
      <button type="submit" id="chat-send" class="btn btn-gold">Send</button>
    </form>
    <div id="voice-status" class="voice-status"></div>
    <div id="chat-reply"></div>
  </section>

  <!-- Module widgets -->
  <div class="section-label">Modules</div>
  <div id="widgets" class="widgets"></div>

  <!-- Board -->
  <div class="section-label">Board</div>
  <div id="board" class="board"><div class="loading">Loading board…</div></div>

  <!-- In Review -->
  <div class="section-label">In Review — needs your sign-off</div>
  <div id="reviews"><div class="loading">Loading…</div></div>
</main>

<script>
const $ = (sel) => document.querySelector(sel);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => (
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));

function fmtDate(iso) {
  if (!iso) return "";
  const m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const p = String(iso).split("-");
  if (p.length < 3) return iso;
  const mo = m[parseInt(p[1],10)-1];
  return mo ? `${mo} ${parseInt(p[2],10)}, ${p[0]}` : iso;
}

function renderWidgets(mods) {
  $("#widgets").innerHTML = mods.map(w => `
    <div class="widget ${esc(w.status)}">
      <div class="wlabel">${esc(w.label)}</div>
      <div class="wstat">${esc(w.stat)}</div>
      <div class="wnote">${esc(w.note)}</div>
    </div>`).join("");
}

function renderBoard(board) {
  $("#board").innerHTML = board.columns.map(col => {
    const cards = col.items.length ? col.items.map(it => {
      const hot = it.category === "HOT" ? '<span class="dot-hot"></span>HOT' : "";
      const due = it.deadline ? "Due " + esc(fmtDate(it.deadline)) : "";
      const sep = hot && due ? " · " : "";
      const meta = (hot || due) ? `<div class="mini-meta">${hot}${sep}${due}</div>` : "";
      const clickable = col.key === "review";
      const attr = clickable ? `class="mini clickable" data-review="${esc(it.id)}"` : 'class="mini"';
      return `<div ${attr}><div class="mini-title">${esc(it.title)}</div>${meta}</div>`;
    }).join("") : '<div class="col-empty">Nothing here yet.</div>';
    return `<div class="col">
      <div class="col-head"><h3>${esc(col.label)}</h3><span class="col-count">${col.count}</span></div>
      <div class="col-blurb">${esc(col.blurb)}</div>
      ${cards}
    </div>`;
  }).join("");
  // Clicking an In Review card on the board jumps to its full card below.
  document.querySelectorAll('.mini.clickable').forEach(el => {
    el.addEventListener('click', () => {
      const card = document.getElementById('review-' + el.dataset.review);
      if (card) { card.scrollIntoView({behavior:'smooth', block:'center'});
                  card.style.borderColor = 'var(--gold-line)';
                  setTimeout(() => card.style.borderColor = '', 1200); }
    });
  });
}

function renderReviews(reviews) {
  const wrap = $("#reviews");
  if (!reviews.length) {
    wrap.innerHTML = '<div class="empty-reviews">Nothing waiting for review right now.</div>';
    return;
  }
  wrap.innerHTML = reviews.map(p => {
    const tag = p.category === "HOT"
      ? '<span class="tag tag-hot">Hot</span>'
      : '<span class="tag tag-std">Std</span>';
    const metaBits = [p.sender, p.amount, p.deadline ? "Due " + p.deadline : ""].filter(Boolean).map(esc);
    const draft = (p.draft || "").trim() || "No draft text yet — it may still be drafting, or the draft lives in the pull request.";
    return `<div class="review" id="review-${esc(p.id)}">
      <div class="review-head">
        <div>
          <h3>${esc(p.title || "Untitled proposal")}</h3>
          <div class="meta">${metaBits.join(" &nbsp;·&nbsp; ")}</div>
        </div>
        ${tag}
      </div>
      <div class="draft-label">Claude's draft</div>
      <div class="draft">${esc(draft)}</div>
      <div class="actions">
        <button class="btn btn-gold btn-sm" data-act="approve" data-id="${esc(p.id)}">✓ Approve</button>
        <button class="btn btn-sm" data-act="toggle" data-id="${esc(p.id)}" data-mode="changes">✎ Request Changes</button>
        <button class="btn btn-sm" data-act="toggle" data-id="${esc(p.id)}" data-mode="reprompt">↺ Re-prompt</button>
      </div>
      <div class="feedback" id="fb-${esc(p.id)}">
        <textarea placeholder="What should Claude change?"></textarea>
        <button class="btn btn-gold btn-sm" data-act="send" data-id="${esc(p.id)}">Send to Claude →</button>
      </div>
      <div class="review-result" id="res-${esc(p.id)}"></div>
    </div>`;
  }).join("");
  wrap.querySelectorAll("[data-act]").forEach(b => b.addEventListener("click", onReviewAction));
}

let _mode = {};  // proposal id -> "changes" | "reprompt"

async function onReviewAction(e) {
  const btn = e.currentTarget;
  const id = btn.dataset.id;
  const act = btn.dataset.act;
  const res = document.getElementById("res-" + id);
  const fb = document.getElementById("fb-" + id);

  if (act === "toggle") {
    _mode[id] = btn.dataset.mode;
    fb.classList.toggle("show");
    if (fb.classList.contains("show")) fb.querySelector("textarea").focus();
    return;
  }

  if (act === "approve") {
    btn.disabled = true;
    const out = await postJSON(`/api/reviews/${encodeURIComponent(id)}/approve`, {});
    showResult(res, out.message || "Done.");
    setTimeout(refresh, 600);
    return;
  }

  if (act === "send") {
    const text = fb.querySelector("textarea").value.trim();
    if (!text) { fb.querySelector("textarea").focus(); return; }
    btn.disabled = true;
    const out = await postJSON(`/api/reviews/${encodeURIComponent(id)}/changes`,
      { feedback: text, mode: _mode[id] || "changes" });
    showResult(res, out.message || "Sent.");
    setTimeout(refresh, 600);
  }
}

function showResult(el, msg) { el.textContent = msg; el.classList.add("show"); }

async function postJSON(url, body) {
  try {
    const r = await fetch(url, {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body),
    });
    return await r.json();
  } catch (err) { return { ok: false, message: "Network error — is the server running?" }; }
}

// ── Chat ──
const chatForm = $("#chat-form");
const chatInput = $("#chat-input");
chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
});
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); chatForm.requestSubmit(); }
});
chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  const send = $("#chat-send");
  const reply = $("#chat-reply");
  send.disabled = true; send.textContent = "Sending…";
  const out = await postJSON("/api/chat", { text });
  reply.textContent = out.message || (out.ok ? "Done." : "Something went wrong.");
  reply.classList.add("show");
  reply.classList.toggle("err", !out.ok);
  if (out.ok) { chatInput.value = ""; chatInput.style.height = "auto"; }
  send.disabled = false; send.textContent = "Send";
  // Refresh now and again shortly, to catch the new ticket landing in review.
  refresh();
  setTimeout(refresh, 4000);
});

// ── Voice input (Web Speech API) ──
// Speech is transcribed into the box so you can read it back and edit before
// sending — voice never auto-submits. Browsers without the API (e.g. Firefox)
// just keep typing; the mic button hides itself.
const micBtn = $("#chat-mic");
const voiceStatus = $("#voice-status");
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recog = null, listening = false, baseText = "", lastError = "";

if (!SR) {
  micBtn.hidden = true;
} else {
  recog = new SR();
  recog.lang = "en-US";
  recog.interimResults = true;
  recog.continuous = false;

  recog.onresult = (e) => {
    let txt = "";
    for (let i = 0; i < e.results.length; i++) txt += e.results[i][0].transcript;
    chatInput.value = (baseText ? baseText + " " : "") + txt.trim();
    chatInput.dispatchEvent(new Event("input"));  // re-size the textarea
  };
  recog.onerror = (e) => {
    lastError = (e.error === "not-allowed" || e.error === "service-not-allowed")
      ? "Mic blocked — allow microphone access in your browser."
      : "Couldn't hear that — try again.";
  };
  recog.onend = () => {
    listening = false;
    micBtn.classList.remove("listening");
    if (lastError) {
      voiceStatus.textContent = lastError; lastError = "";
      voiceStatus.classList.add("show");
      setTimeout(() => voiceStatus.classList.remove("show"), 3000);
    } else {
      voiceStatus.classList.remove("show");
    }
    chatInput.focus();
  };

  micBtn.addEventListener("click", () => {
    if (listening) { recog.stop(); return; }
    baseText = chatInput.value.trim();
    try { recog.start(); } catch (_) { return; }  // start() throws if already running
    listening = true;
    micBtn.classList.add("listening");
    voiceStatus.textContent = "🎙 Listening… tap the mic again to stop, then review and Send.";
    voiceStatus.classList.add("show");
  });
}

// ── State / polling ──
async function refresh() {
  let s;
  try {
    const r = await fetch("/api/state");
    s = await r.json();
  } catch (err) { return; }
  $("#demo-banner").classList.toggle("show", !!s.demo);
  renderWidgets(s.modules);
  renderBoard(s.board);
  renderReviews(s.reviews);
}

refresh();
setInterval(refresh, 30000);
</script>
<!--FOOTER-->
</body>
</html>
"""

# Inject the shared top nav, footer (quick links + tour button) and the tour
# engine — all single-sourced in theme.py — so the work board stays in step
# with the module pages.
# Bake the static shell once; <!--NAV--> is left in place and filled per-request
# in index() so module gating + the catalog badge stay live.
PAGE = (
    PAGE.replace("<!--TITLE-->", profile.ACTIVE["name"])
    .replace("<!--FONTS-->", theme.FONT_LINK)
    .replace("/*ROOTCSS*/", profile.root_css())
    .replace("/*EXTRA_CSS*/", theme.EXTRA_CSS)
    .replace("<!--FOOTER-->", theme.footer()
             + f"<script>{theme.TOUR_JS}</script><script>{theme.VIEW_JS}</script>")
)
