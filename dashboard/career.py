"""Career — job search workspace: applications, a to-do checklist, and notes.

Three editable sections:
- Applications: each company with a status and free-text notes (recruiter,
  contact, next step).
- To-do: a simple checklist (toggle done, add/remove, edit inline).
- Notes: titled note cards for prep, questions, non-negotiables, exit talking
  points — whatever's worth keeping in one place.

Ships blank, like every module — the editing UI fills it in; nothing personal
is seeded in code. State persists to the store.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from . import store, theme

router = APIRouter()

# Sample workspace for inspiration — shown until you make it your own.
DEFAULT = {
    "applications": [
        {"id": "c-example", "company": "Dream Company", "stage": "Interested", "status": "",
         "note": "A role that fits — tailor the résumé before applying."},
    ],
    "todos": [
        {"id": "td-resume", "text": "Refresh my résumé", "done": False},
        {"id": "td-reach", "text": "Reach out to one contact this week", "done": False},
    ],
    "notes": [
        {"id": "n-pitch", "title": "My pitch", "body": "Two sentences on what I do and the impact I've had."},
    ],
}


def _data() -> dict:
    d = store.load("career", DEFAULT)
    for k in ("applications", "todos", "notes"):
        d.setdefault(k, [])
    return d


def _id() -> str:
    return uuid.uuid4().hex[:8]


@router.get("/api/career")
async def get_career() -> JSONResponse:
    return JSONResponse(_data())


@router.post("/api/career")
async def save_career(body: dict) -> JSONResponse:
    """Replace the whole workspace. Empty rows are dropped; ids are preserved
    (or minted) so edits stay stable across saves."""
    apps = [{
        "id": (a.get("id") or _id()),
        "company": (a.get("company") or "").strip(),
        "stage": (a.get("stage") or "Interested").strip(),
        "status": (a.get("status") or "").strip(),
        "note": (a.get("note") or "").strip(),
    } for a in body.get("applications", []) if (a.get("company") or "").strip()]
    todos = [{
        "id": (t.get("id") or _id()),
        "text": (t.get("text") or "").strip(),
        "done": bool(t.get("done")),
    } for t in body.get("todos", []) if (t.get("text") or "").strip()]
    notes = [{
        "id": (n.get("id") or _id()),
        "title": (n.get("title") or "").strip(),
        "body": (n.get("body") or "").strip(),
    } for n in body.get("notes", []) if (n.get("title") or "").strip() or (n.get("body") or "").strip()]
    d = {"applications": apps, "todos": todos, "notes": notes}
    store.save("career", d)
    return JSONResponse(d)


@router.get("/career", response_class=HTMLResponse)
async def career_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Career & Business Growth", _BODY, active="career"))


_BODY = r"""
<style>
  .c-head h1 { font-size: 42px; } .c-head h1 b { color: var(--gold); font-weight: 400; }
  .c-sub { font-size: 12.5px; color: var(--muted); margin: 4px 0 8px; }
  .sec { font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--gold); margin: 30px 0 12px; }
  /* inline editors — read as text until hovered/focused */
  .ed { background: transparent; border: 1px solid transparent; border-radius: 7px; color: inherit; font-family: inherit; font-size: inherit; padding: 4px 7px; box-sizing: border-box; width: 100%; }
  .ed:hover { border-color: var(--line-soft); }
  .ed:focus { outline: none; border-color: var(--gold-line); background: var(--field); }
  textarea.ed { resize: vertical; line-height: 1.6; }
  .app { background: var(--panel); border: 1px solid var(--line-soft); border-left: 3px solid var(--line); border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }
  .app[data-stage="Interested"]      { border-left-color: #8794b3; }
  .app[data-stage="Applied"]         { border-left-color: #6b8cce; }
  .app[data-stage="Referral"]        { border-left-color: #b07cd8; }
  .app[data-stage="Recruiter call"]  { border-left-color: var(--gold); }
  .app[data-stage="Hiring manager"]  { border-left-color: #E8A87C; }
  .app[data-stage="Onsite"]          { border-left-color: #5bc0be; }
  .app[data-stage="Offer"]           { border-left-color: #80D4A0; }
  .app[data-stage="On hold"]         { border-left-color: #6b7280; }
  .app[data-stage="Rejected"]        { border-left-color: #F08080; }
  .app-top { display: flex; align-items: center; gap: 8px; }
  .app-top .company { font-size: 15px; font-weight: 600; flex: 1; }
  .ed.stage { flex: 0 0 150px; color: var(--gold); cursor: pointer; }
  .app .status { color: var(--muted); font-size: 12px; }
  .app .note { font-size: 12.5px; color: var(--muted); margin-top: 2px; }
  .todo { display: flex; align-items: center; gap: 10px; padding: 4px 0; }
  .todo .box { width: 18px; height: 18px; border-radius: 6px; border: 2px solid var(--line); flex-shrink: 0; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 11px; }
  .todo.done .box { background: #80D4A0; border-color: #80D4A0; color: var(--bg); }
  .todo .tx { flex: 1; font-size: 13.5px; } .todo.done .tx { text-decoration: line-through; color: var(--muted); }
  .note-card { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 12px; padding: 12px 14px; margin-bottom: 10px; }
  .note-card .nhead { display: flex; align-items: center; gap: 8px; }
  .note-card .ntitle { font-size: 14px; font-weight: 600; flex: 1; }
  .note-card .nbody { font-size: 13px; color: var(--muted); margin-top: 4px; min-height: 60px; }
  .addrow { display: flex; gap: 8px; margin: 8px 0 4px; flex-wrap: wrap; }
  .addrow input { flex: 1; min-width: 90px; }
  .x { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 13px; flex-shrink: 0; }
  .x:hover { color: #F08080; }
  .empty { color: var(--muted); font-style: italic; font-size: 13px; padding: 4px 0; }
</style>

<main>
  <div class="c-head"><h1>Career &amp; Business Growth 📈</h1></div>
  <p class="c-sub">applications, prep &amp; the plan — tap any line to edit</p>

  <div class="sec">Applications</div>
  <div id="apps"></div>
  <div class="addrow">
    <input id="a-company" type="text" placeholder="Company">
    <input id="a-status" type="text" placeholder="Status — e.g. Recruiter call Jun 24">
    <button class="btn btn-gold btn-sm" id="a-add">Add</button>
  </div>

  <div class="sec">To-Do</div>
  <div id="todos"></div>
  <div class="addrow">
    <input id="t-text" type="text" placeholder="A task">
    <button class="btn btn-gold btn-sm" id="t-add">Add</button>
  </div>

  <div class="sec">Notes</div>
  <div id="notes"></div>
  <div class="addrow">
    <input id="n-title" type="text" placeholder="Note title — e.g. K2 Call Prep">
    <button class="btn btn-gold btn-sm" id="n-add">Add</button>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { applications: [], todos: [], notes: [] };
const find = (list, id) => data[list].find(x => x.id === id);
const STAGES = ["Interested", "Applied", "Referral", "Recruiter call", "Hiring manager", "Onsite", "Offer", "On hold", "Rejected"];
const stageOpts = (sel) => STAGES.map(s => `<option ${s === sel ? "selected" : ""}>${s}</option>`).join("");

function render() {
  // Applications
  $("#apps").innerHTML = data.applications.length ? data.applications.map(a => `<div class="app" data-stage="${esc(a.stage || "Interested")}">
    <div class="app-top">
      <input class="ed company" data-list="applications" data-f="company" data-id="${esc(a.id)}" value="${esc(a.company)}" placeholder="Company">
      <select class="ed stage" data-list="applications" data-f="stage" data-id="${esc(a.id)}">${stageOpts(a.stage || "Interested")}</select>
      <button class="x" data-rm="applications" data-id="${esc(a.id)}">✕</button>
    </div>
    <input class="ed status" data-list="applications" data-f="status" data-id="${esc(a.id)}" value="${esc(a.status)}" placeholder="Detail — e.g. Recruiter call Tue Jun 24, 4PM">
    <textarea class="ed note" data-list="applications" data-f="note" data-id="${esc(a.id)}" rows="2" placeholder="Recruiter, contact, next step…">${esc(a.note)}</textarea>
  </div>`).join("") : '<div class="empty">No applications yet — add one below.</div>';

  // To-do
  $("#todos").innerHTML = data.todos.length ? data.todos.map(t => `<div class="todo ${t.done ? "done" : ""}">
    <div class="box" data-toggle="${esc(t.id)}">${t.done ? "✓" : ""}</div>
    <input class="ed tx" data-list="todos" data-f="text" data-id="${esc(t.id)}" value="${esc(t.text)}" placeholder="A task">
    <span class="x" data-rm="todos" data-id="${esc(t.id)}">✕</span>
  </div>`).join("") : '<div class="empty">Nothing to do yet — add a task below.</div>';

  // Notes
  $("#notes").innerHTML = data.notes.length ? data.notes.map(n => `<div class="note-card">
    <div class="nhead">
      <input class="ed ntitle" data-list="notes" data-f="title" data-id="${esc(n.id)}" value="${esc(n.title)}" placeholder="Title">
      <button class="x" data-rm="notes" data-id="${esc(n.id)}">✕</button>
    </div>
    <textarea class="ed nbody" data-list="notes" data-f="body" data-id="${esc(n.id)}" rows="3" placeholder="…">${esc(n.body)}</textarea>
  </div>`).join("") : '<div class="empty">No notes yet — add one below.</div>';

  // Inline field edits — persist on blur, no re-render (stay in flow)
  document.querySelectorAll("[data-f]").forEach(el => el.addEventListener("change", () => {
    const item = find(el.dataset.list, el.dataset.id); if (!item) return;
    item[el.dataset.f] = el.value; persist(el.dataset.f === "stage");  // stage recolors the card
  }));
  // To-do toggle
  document.querySelectorAll("[data-toggle]").forEach(el => el.addEventListener("click", () => {
    const t = find("todos", el.dataset.toggle); if (!t) return; t.done = !t.done; save();
  }));
  // Remove
  document.querySelectorAll("[data-rm]").forEach(el => el.addEventListener("click", () => {
    const list = el.dataset.rm; data[list] = data[list].filter(x => x.id !== el.dataset.id); save();
  }));
}

const rid = () => Math.random().toString(36).slice(2, 10);
async function persist(reRender) {
  try { data = await (await fetch("/api/career", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) })).json(); } catch (_) {}
  if (reRender) render();
}
const save = () => persist(true);

function addApp() {
  const company = $("#a-company").value.trim(); if (!company) return;
  data.applications.push({ id: rid(), company, stage: "Interested", status: $("#a-status").value.trim(), note: "" });
  $("#a-company").value = ""; $("#a-status").value = ""; save();
}
function addTodo() {
  const text = $("#t-text").value.trim(); if (!text) return;
  data.todos.push({ id: rid(), text, done: false }); $("#t-text").value = ""; save();
}
function addNote() {
  const title = $("#n-title").value.trim(); if (!title) return;
  data.notes.push({ id: rid(), title, body: "" }); $("#n-title").value = ""; save();
}
$("#a-add").addEventListener("click", addApp);
$("#t-add").addEventListener("click", addTodo);
$("#n-add").addEventListener("click", addNote);
[["#a-company", addApp], ["#a-status", addApp], ["#t-text", addTodo], ["#n-title", addNote]]
  .forEach(([sel, fn]) => $(sel).addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); fn(); } }));

(async () => { try { data = await (await fetch("/api/career")).json(); } catch (_) {} render(); })();
</script>
"""
