"""USAFA and Dev work surfaces — dedicated, filtered views of the Jira board.

The board (reviewer.get_dashboard) carries every kind of work Neo creates, told
apart by the summary prefix Neo writes:

- "USAFA — …"     → USAFA web-dev tasks
- "Proposal — …"  → proposals
- everything else → the app's own dev / maintenance tickets

They used to share one board, so the headline use case (USAFA) was buried. This
module splits USAFA and Dev onto their own pages:

- /usafa  — a request bar + a USAFA-only board (dad's web-dev workspace)
- /dev    — the app's build/maintenance tickets, on their own board

The Proposals board (and its Approve / Request-Changes review queue) stays in
main.py; here we only need the board, and a request bar for USAFA.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from reviewer.dashboard_api import DEMO_MODE as BOARD_DEMO
from reviewer.dashboard_api import JIRA_BASE_URL, get_dashboard

from . import chat, theme

router = APIRouter()


def classify(title: str) -> str:
    """Which surface a ticket belongs to, from its summary prefix."""
    s = (title or "").strip().lower()
    if s.startswith("usafa"):
        return "usafa"
    if s.startswith("proposal"):
        return "proposal"
    return "dev"


def filtered_board(kind: str) -> dict:
    """The live board, keeping only the columns' items that belong to `kind`."""
    board = get_dashboard()
    cols = []
    total = 0
    for col in board["columns"]:
        items = [it for it in col["items"] if classify(it.get("title", "")) == kind]
        total += len(items)
        cols.append({**col, "items": items, "count": len(items)})
    return {"total": total, "columns": cols}


# ── API ────────────────────────────────────────────────────────────────────────
@router.get("/api/work/{kind}")
async def work_state(kind: str) -> JSONResponse:
    kind = kind if kind in ("usafa", "dev") else "usafa"
    return JSONResponse({
        "demo": BOARD_DEMO,
        "board": filtered_board(kind),
        "jira_base": (JIRA_BASE_URL or "").rstrip("/"),
    })


class ReqIn(BaseModel):
    text: str


@router.post("/api/work/usafa/request")
async def usafa_request(body: ReqIn, background: BackgroundTasks) -> JSONResponse:
    """Open a USAFA web-dev ticket and start the draft — always routes to the
    USAFA module (no intent guessing on this page)."""
    result = chat.start_request(body.text, module="usafa")
    if result.get("ok") and not result.get("demo"):
        background.add_task(chat.run_draft, result["ticket"], result["title"], body.text, result["module"])
    return JSONResponse(result)


# ── Pages ──────────────────────────────────────────────────────────────────────
@router.get("/usafa", response_class=HTMLResponse)
async def usafa_page() -> HTMLResponse:
    return HTMLResponse(theme.page("USAFA", _body("usafa"), active="usafa"))


@router.get("/dev", response_class=HTMLResponse)
async def dev_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Dev", _body("dev"), active="dev"))


_HEAD = {
    "usafa": ("USAFA <b>web-dev</b>", "Describe a change to the Academy site — Neo drafts it and opens a PR for sign-off."),
    "dev": ("Neo <b>dev</b>", "Build &amp; maintenance tickets for the dashboard itself."),
}


def _body(kind: str) -> str:
    head_title, head_sub = _HEAD[kind]
    request_bar = "" if kind != "usafa" else r"""
  <section class="reqbar">
    <form id="req-form" class="req-row">
      <textarea id="req-input" rows="1" placeholder="e.g. Add an athletics schedule page to the USAFA site"></textarea>
      <button type="button" id="req-mic" class="btn btn-mic" aria-label="Speak your request" title="Speak your request">🎙</button>
      <button type="submit" class="btn btn-gold" id="req-send">Request</button>
    </form>
    <div id="req-voice" class="req-voice"></div>
    <div id="req-reply"></div>
  </section>
"""
    return f"""
<style>
  .w-head h1 {{ font-size: 42px; }} .w-head h1 b {{ color: var(--gold); font-weight: 400; }}
  .w-sub {{ font-size: 12.5px; color: var(--muted); margin: 4px 0 22px; max-width: 640px; line-height: 1.5; }}
  .reqbar {{ background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 18px; margin-bottom: 26px; }}
  .req-row {{ display: flex; gap: 8px; align-items: flex-end; }}
  .req-row textarea {{ flex: 1; background: var(--field); border: 1px solid var(--line-soft); border-radius: 10px; color: var(--text);
    font-family: inherit; font-size: 13px; padding: 11px 13px; resize: none; line-height: 1.5; box-sizing: border-box; }}
  .req-row textarea:focus {{ outline: none; border-color: var(--gold-line); }}
  .btn-mic {{ background: var(--field); border: 1px solid var(--line-soft); color: var(--muted); border-radius: 10px; padding: 0 12px; cursor: pointer; font-size: 15px; }}
  .btn-mic.rec {{ color: var(--gold); border-color: var(--gold-line); }}
  .req-voice {{ font-size: 11px; color: var(--muted); margin-top: 8px; min-height: 14px; }}
  #req-reply {{ font-size: 13px; margin-top: 12px; line-height: 1.55; }}
  #req-reply .ok {{ color: #80D4A0; }} #req-reply .err {{ color: #F08080; }}
  .demo-tag {{ display: inline-block; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--hot);
    border: 1px solid var(--hot); border-radius: 20px; padding: 1px 9px; margin-bottom: 16px; }}
  .board {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; align-items: start; }}
  @media (max-width: 900px) {{ .board {{ grid-template-columns: repeat(2, 1fr); }} }}
  .col {{ background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; padding: 14px; }}
  .col-head {{ display: flex; justify-content: space-between; align-items: center; font-size: 11px; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }}
  .col-head .n {{ background: var(--field); border-radius: 20px; padding: 1px 8px; color: var(--text); }}
  .col.review .col-head {{ color: var(--gold); }}
  .col-cards {{ max-height: 62vh; overflow-y: auto; margin: 0 -4px; padding: 0 4px; }}
  .col-cards::-webkit-scrollbar {{ width: 6px; }}
  .col-cards::-webkit-scrollbar-thumb {{ background: var(--line); border-radius: 3px; }}
  .card {{ display: block; background: var(--field); border: 1px solid var(--line-soft); border-left: 3px solid var(--gold);
    border-radius: 10px; padding: 11px 13px; margin-bottom: 9px; text-decoration: none; color: inherit; transition: border-color 0.15s; }}
  .card:hover {{ border-color: var(--gold-line); }}
  .card .ct {{ font-size: 13px; line-height: 1.4; }}
  .card .cm {{ font-size: 10px; color: var(--muted); margin-top: 6px; letter-spacing: 0.04em; }}
  .col-empty {{ font-size: 12px; color: var(--muted); font-style: italic; padding: 4px 2px; }}
  .loading {{ color: var(--muted); font-style: italic; }}
</style>

<main>
  <div class="w-head"><h1>{head_title}</h1></div>
  <p class="w-sub">{head_sub}</p>
  <div id="demo-tag"></div>
{request_bar}
  <div id="board" class="board"><div class="loading">Loading board…</div></div>
</main>

<script>
const KIND = "{kind}";
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c])));
let jiraBase = "";

function card(it) {{
  const href = jiraBase ? `${{jiraBase}}/browse/${{esc(it.id)}}` : "#";
  const due = it.deadline ? `Due ${{esc(it.deadline)}}` : "";
  const meta = [`${{esc(it.id)}} ↗`, due].filter(Boolean).join(" · ");
  return `<a class="card" href="${{href}}" target="_blank" rel="noopener">
    <div class="ct">${{esc(it.title)}}</div><div class="cm">${{meta}}</div></a>`;
}}

function renderBoard(board) {{
  $("#board").innerHTML = board.columns.map(col => `
    <div class="col ${{col.key === "review" ? "review" : ""}}">
      <div class="col-head"><span>${{esc(col.label)}}</span><span class="n">${{col.count}}</span></div>
      <div class="col-cards">${{col.items.length ? col.items.map(card).join("") : '<div class="col-empty">—</div>'}}</div>
    </div>`).join("");
}}

async function load() {{
  try {{
    const s = await (await fetch(`/api/work/${{KIND}}`)).json();
    jiraBase = s.jira_base || "";
    $("#demo-tag").innerHTML = s.demo ? '<span class="demo-tag">Demo mode</span>' : "";
    renderBoard(s.board);
  }} catch (_) {{}}
}}

// USAFA request bar (only present on /usafa)
const form = $("#req-form");
if (form) {{
  const inp = $("#req-input"), reply = $("#req-reply");
  form.addEventListener("submit", async (e) => {{
    e.preventDefault();
    const text = inp.value.trim(); if (!text) return;
    $("#req-send").disabled = true; reply.textContent = "Opening the ticket…";
    try {{
      const out = await (await fetch("/api/work/usafa/request", {{ method:"POST", headers:{{"Content-Type":"application/json"}}, body: JSON.stringify({{ text }}) }})).json();
      reply.innerHTML = `<span class="${{out.ok ? "ok" : "err"}}">${{esc(out.message || "")}}</span>`;
      if (out.ok) {{ inp.value = ""; setTimeout(load, 600); }}
    }} catch (_) {{ reply.innerHTML = '<span class="err">Something went wrong — try again.</span>'; }}
    $("#req-send").disabled = false;
  }});
  // Voice input (Web Speech API), matching the dashboard chat mic.
  const mic = $("#req-mic"), vs = $("#req-voice");
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR && mic) {{
    let rec = null, on = false;
    mic.addEventListener("click", () => {{
      if (on) {{ rec && rec.stop(); return; }}
      rec = new SR(); rec.lang = "en-US"; rec.interimResults = true;
      const base = inp.value ? inp.value + " " : "";
      rec.onstart = () => {{ on = true; mic.classList.add("rec"); vs.textContent = "Listening…"; }};
      rec.onresult = (ev) => {{ let t = ""; for (const r of ev.results) t += r[0].transcript; inp.value = base + t; }};
      rec.onerror = () => {{ vs.textContent = "Mic error — type instead."; }};
      rec.onend = () => {{ on = false; mic.classList.remove("rec"); vs.textContent = ""; }};
      rec.start();
    }});
  }} else if (mic) {{ mic.style.display = "none"; }}
}}

load();
setInterval(load, 30000);
</script>
"""
