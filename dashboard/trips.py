"""Trips (NEO-43) — travel planner, ported from the Aria reference app.

Trips with a status, dates, flight details, a per-audience note, and a to-do
checklist. View-modes are first-class here: flight + confirmation are
Private-only, the note text changes per audience (you write a different line
for Friends vs Coworker vs Public), and each to-do declares which views it
shows in. State persists to the store.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from . import store, theme

router = APIRouter()

# Sample trips for inspiration — shown until you add your own.
DEFAULT = {"trips": [
    {"id": "t-banff", "emoji": "🏔️", "city": "Banff, Canada", "dates": "Aug 14–20", "status": "planning"},
    {"id": "t-cdmx", "emoji": "🌮", "city": "Mexico City", "dates": "Oct 2026", "status": "booked"},
]}


def _data() -> dict:
    return store.load("trips", DEFAULT)


@router.get("/api/trips")
async def get_trips() -> JSONResponse:
    return JSONResponse(_data())


@router.post("/api/trips")
async def save_trips(body: dict) -> JSONResponse:
    data = {"trips": body.get("trips", [])}
    store.save("trips", data)
    return JSONResponse(data)


@router.get("/trips", response_class=HTMLResponse)
async def trips_page() -> HTMLResponse:
    return HTMLResponse(theme.page("Recreation, Fun & Travel", _BODY, active="trips"))


_BODY = r"""
<style>
  .t-head h1 { font-size: 40px; } .t-head h1 b { color: var(--gold); font-weight: 400; }
  .t-sub { font-size: 12.5px; color: var(--muted); margin: 2px 0 22px; }
  .trip { background: var(--panel); border: 1px solid var(--line-soft); border-radius: 14px; margin-bottom: 14px; border-left: 3px solid var(--gold); overflow: hidden; }
  .trip-top { padding: 18px 20px; display: flex; align-items: center; justify-content: space-between; gap: 12px; cursor: pointer; }
  .trip-left { display: flex; align-items: center; gap: 14px; }
  .trip-city { font-size: 18px; } .trip-dates { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .status { font-size: 11px; padding: 3px 10px; border-radius: 20px; white-space: nowrap; }
  .status.booked { color: #80D4A0; background: rgba(128,212,160,0.12); border: 1px solid rgba(128,212,160,0.4); }
  .status.planning { color: #F0D080; background: rgba(240,208,128,0.12); border: 1px solid rgba(240,208,128,0.4); }
  .trip-body { padding: 4px 20px 20px; border-top: 1px solid var(--line-soft); }
  .ed-lbl { font-size: 9px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); margin: 16px 0 7px; }
  .trip-body input, .trip-body textarea, .trip-body select {
    width: 100%; background: var(--field); border: 1px solid var(--line-soft); border-radius: 9px;
    color: var(--text); font-family: inherit; font-size: 12.5px; padding: 9px 11px; box-sizing: border-box; }
  .trip-body textarea { resize: vertical; line-height: 1.7; }
  .trip-body input:focus, .trip-body textarea:focus, .trip-body select:focus { outline: none; border-color: var(--gold-line); }
  .meta-row { display: flex; gap: 8px; }
  .meta-row .dt { flex: 1; } .meta-row .st { width: 130px; }
  .cf-inp { margin-top: 8px; }
  .todos { margin-top: 16px; }
  .todos .tl { font-size: 9px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); margin-bottom: 10px; }
  .todo { display: flex; align-items: center; gap: 10px; padding: 5px 0; }
  .todo .box { width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--gold); flex-shrink: 0; cursor: pointer; }
  .todo .tx { flex: 1; cursor: pointer; }
  .todo.done .box { background: var(--gold); } .todo.done .tx { text-decoration: line-through; color: var(--muted); }
  .todo .td-rm { color: var(--muted); cursor: pointer; font-size: 12px; padding: 0 4px; opacity: 0.6; }
  .todo .td-rm:hover { color: #F08080; opacity: 1; }
  .add-todo { display: flex; gap: 8px; margin-top: 10px; }
  .add-todo input { flex: 1; } .add-todo button { flex-shrink: 0; }
  .add { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
  .add input.e { width: 48px; text-align: center; } .add input.c { flex: 1; min-width: 120px; } .add input.d { width: 130px; }
</style>

<main>
  <div class="t-head"><h1>Recreation, Fun &amp; <b>Travel 🌴</b></h1></div>
  <p class="t-sub">where to next — tap a trip to edit flights, notes & to-dos</p>
  <div id="trips"></div>
  <div class="add">
    <input class="e" id="a-emoji" type="text" value="📍">
    <input class="c" id="a-city" type="text" placeholder="City">
    <input class="d" id="a-dates" type="text" placeholder="Dates / TBD">
    <select id="a-status"><option value="planning">Planning</option><option value="booked">Booked</option></select>
    <button class="btn btn-gold btn-sm" id="a-btn">Add trip</button>
  </div>
</main>

<script>
const $ = (s) => document.querySelector(s);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])));
let data = { trips: [] };
let open = null;

const trip = (id) => data.trips.find(x => String(x.id) === String(id));

function tripCard(t) {
  const isOpen = String(open) === String(t.id);
  const todos = t.todos || [];
  const noteVal = (t.notes && t.notes.private) || "";
  return `<div class="trip">
    <div class="trip-top" data-open="${esc(String(t.id))}">
      <div class="trip-left"><span style="font-size:26px">${esc(t.emoji)}</span>
        <div><div class="trip-city">${esc(t.city)}</div><div class="trip-dates">${esc(t.dates)}</div></div></div>
      <div style="display:flex;align-items:center;gap:10px">
        <span class="status ${esc(t.status)}">${t.status === "booked" ? "✓ Booked" : "🗓️ Planning"}</span>
        <span style="color:var(--muted)">${isOpen ? "▲" : "▼"}</span></div>
    </div>
    ${isOpen ? `<div class="trip-body">
      <div class="ed-lbl">Dates & status</div>
      <div class="meta-row">
        <input class="dt" data-f="dates" data-id="${esc(String(t.id))}" value="${esc(t.dates)}" placeholder="Dates / TBD">
        <select class="st" data-f="status" data-id="${esc(String(t.id))}">
          <option value="planning" ${t.status === "planning" ? "selected" : ""}>Planning</option>
          <option value="booked" ${t.status === "booked" ? "selected" : ""}>Booked</option>
        </select>
      </div>

      <div class="ed-lbl">Flight</div>
      <textarea data-f="flight" data-id="${esc(String(t.id))}" rows="2" placeholder="UA 1234 · IAD→AUS · Aug 28&#10;UA 5678 · AUS→IAD · Aug 30">${esc(t.flight || "")}</textarea>
      <input class="cf-inp" data-f="confirmation" data-id="${esc(String(t.id))}" value="${esc(t.confirmation || "")}" placeholder="Confirmation #">

      <div class="ed-lbl">Note</div>
      <textarea data-f="note" data-id="${esc(String(t.id))}" rows="2" placeholder="A note for this trip…">${esc(noteVal)}</textarea>

      <div class="todos"><div class="tl">To-do</div>
        ${todos.map(td => `<div class="todo ${td.done ? "done" : ""}">
          <div class="box" data-toggle="${esc(String(td.id))}" data-id="${esc(String(t.id))}"></div>
          <span class="tx" data-toggle="${esc(String(td.id))}" data-id="${esc(String(t.id))}">${esc(td.text)}</span>
          <span class="td-rm" data-tdrm="${esc(String(td.id))}" data-id="${esc(String(t.id))}">✕</span></div>`).join("")}
        <div class="add-todo">
          <input class="td-new" data-id="${esc(String(t.id))}" placeholder="Add a to-do…">
          <button class="btn btn-sm td-add" data-id="${esc(String(t.id))}">＋ Add</button>
        </div>
      </div>

      <div style="margin-top:16px"><span class="btn btn-sm rm" data-rm="${esc(String(t.id))}" style="color:#F08080">🗑 remove trip</span></div>
    </div>` : ""}
  </div>`;
}

function render() {
  $("#trips").innerHTML = data.trips.map(tripCard).join("") || '<div style="color:var(--muted);font-style:italic">No trips yet — add one below.</div>';

  // Expand / collapse
  $("#trips").querySelectorAll("[data-open]").forEach(el => el.addEventListener("click", () => {
    open = String(open) === el.dataset.open ? null : el.dataset.open; render();
  }));

  // Field edits — persist on blur/change, no re-render (keeps you in flow)
  $("#trips").querySelectorAll("[data-f]").forEach(el => el.addEventListener("change", () => {
    const t = trip(el.dataset.id); if (!t) return;
    const f = el.dataset.f, val = el.value;
    if (f === "note") { t.notes = t.notes || {}; t.notes.private = val; }
    else { t[f] = val; }
    persist(f === "status");  // status changes the badge -> re-render
  }));

  // To-do toggle
  $("#trips").querySelectorAll("[data-toggle]").forEach(el => el.addEventListener("click", () => {
    const t = trip(el.dataset.id); if (!t) return;
    const td = (t.todos || []).find(x => String(x.id) === el.dataset.toggle);
    if (td) { td.done = !td.done; save(); }
  }));

  // To-do remove
  $("#trips").querySelectorAll("[data-tdrm]").forEach(el => el.addEventListener("click", () => {
    const t = trip(el.dataset.id); if (!t) return;
    t.todos = (t.todos || []).filter(x => String(x.id) !== el.dataset.tdrm); save();
  }));

  // To-do add (button or Enter)
  const addTodo = (id) => {
    const inp = $("#trips").querySelector(`.td-new[data-id="${id}"]`);
    const text = inp && inp.value.trim(); if (!text) return;
    const t = trip(id); if (!t) return;
    t.todos = t.todos || [];
    t.todos.push({ id: Date.now(), text, done: false, views: ["private"] });
    save();
  };
  $("#trips").querySelectorAll(".td-add").forEach(el => el.addEventListener("click", () => addTodo(el.dataset.id)));
  $("#trips").querySelectorAll(".td-new").forEach(el => el.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); addTodo(el.dataset.id); }
  }));

  // Remove trip
  $("#trips").querySelectorAll("[data-rm]").forEach(el => el.addEventListener("click", () => {
    data.trips = data.trips.filter(x => String(x.id) !== el.dataset.rm); save();
  }));
}

// Persist to the store. reRender=false keeps focus/scroll steady after a text edit.
async function persist(reRender) {
  try {
    const fresh = await (await fetch("/api/trips", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(data) })).json();
    data = fresh;
  } catch (_) {}
  if (reRender) render();
}
const save = () => persist(true);

$("#a-btn").addEventListener("click", () => {
  const city = $("#a-city").value.trim(); if (!city) return;
  data.trips.push({ id: Date.now(), city, emoji: $("#a-emoji").value.trim() || "📍", status: $("#a-status").value,
    dates: $("#a-dates").value.trim() || "TBD", flight: "", confirmation: "",
    notes: { private: "", friends: "", coworker: "", public: "" }, todos: [] });
  $("#a-city").value = ""; $("#a-dates").value = ""; $("#a-emoji").value = "📍"; save();
});

(async () => { try { data = await (await fetch("/api/trips")).json(); } catch (_) {} render(); })();
</script>
"""
